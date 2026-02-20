"""
Ce script constitue le module principal d’extraction et d’enrichissement
des données brevets issues de l’API EPO OPS (European Patent Office –
Open Patent Services), dans le cadre du projet Fil Rouge.


USAGE:
    Penser à autoriser l'application sur le portail développeur EPO (validité 20 min) (l'appli s'appelle : fil-rouge-v2-inpi-ai)
    https://developers.epo.org/user/31706/app-detail/ed3afe02-dce8-47ef-a214-fd5a96a82652

    Lancer le serveur :
        uv run uvicorn main:app --reload
    Puis :
        uv run python -m crawlers.Inpi_Bulk

    => va générer un fichier 'epo_ai_brevets.jsonl' dans /data/
    => va enregistrer les lignes dans la database.db

QUERY: 'ti=artificial intelligence'
       Le script interroge l'API EPO OPS de manière incrémentale par blocs de 100.

EXPLICATIONS:
    Fonctionne en complément avec Inpi_fetcher.py.
    Logique métier + écriture fichier + insertion DB.
    Récupère les brevets (type 'patent'), extrait la bibliographie et les résumés.
    Intègre les données dans la table 'RESEARCH_ITEM' de la database.db.
    Génère un JSONL pour la visualisation (limité aux 100 premiers de la session),
    tandis que l'intégralité (jusqu'à 10 000) est injectée en base de données.

OBSERVATIONS:
    Les brevets n'ont pas de DOI ; l'identifiant DOCDB (ex: US20260038635) fait office de clé unique.
    Respecte les quotas OPS (Fair Use Policy) via un throttling strict (pauses de 1.5s).
    Le 'family_id' permet de regrouper les brevets d'une même invention.
"""

import json
import time
import os
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

from .Inpi_fetcher import InpiFetcher
from database import get_session
from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from services.author_service import AuthorService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate
from schemas.author import AuthorCreate


# -------------------------
# Configuration & Initialisation
# -------------------------
load_dotenv()

QUERIES = ["ti=artificial intelligence"]
MAX_RECORDS_DB = 10_000  # Limite totale pour la BDD
MAX_RECORDS_JSON = 100  # Limite pour le fichier JSONL de visualisation
STEP = 100  # Pagination API OPS

fetcher = InpiFetcher(
    os.getenv("EPO_CLIENT_ID"),
    os.getenv("EPO_CLIENT_SECRET"),
)

# Initialisation DB
session = next(get_session())
source_service = SourceService()
item_service = ResearchItemService()
author_service = AuthorService()

# Création de la source EPO
epo_source = source_service.create(
    session,
    SourceCreate(name="epo_ops", type="patent", base_url="https://ops.epo.org/"),
)

Path("data").mkdir(exist_ok=True)
output_path = Path("data/epo_ai_brevets.jsonl")

# Chargement des IDs existants pour éviter les doublons au sein du crawl
existing_docdb_ids = set()
if output_path.exists():
    with open(output_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                if "docdb_id" in obj:
                    existing_docdb_ids.add(obj["docdb_id"])
            except json.JSONDecodeError:
                continue


# -------------------------
# Fonctions de Parsing
# -------------------------


def extract_publication_references(xml_text):
    ns = {
        "ops": "http://ops.epo.org",
        "ex": "http://www.epo.org/exchange",
    }

    root = ET.fromstring(xml_text)
    results = []

    for pub in root.findall(".//ops:publication-reference", ns):
        family_id = pub.get("family-id")

        doc = pub.find("ex:document-id[@document-id-type='docdb']", ns)
        if doc is None:
            continue

        country = doc.findtext("ex:country", namespaces=ns)
        doc_number = doc.findtext("ex:doc-number", namespaces=ns)
        kind = doc.findtext("ex:kind", namespaces=ns)

        if not all([family_id, country, doc_number]):
            continue

        results.append(
            {
                "family_id": family_id,
                "docdb_id": f"{country}{doc_number}",
                "country": country,
                "doc_number": doc_number,
                "kind": kind,
            }
        )

    return results


# -------------------------
# Parsing ciblé
# -------------------------


def parse_biblio(xml_text):
    ns = {"ex": "http://www.epo.org/exchange"}
    root = ET.fromstring(xml_text)

    data = {
        "title": None,
        "applicants": [],
        "inventors": [],
        "cpc": [],
    }

    titles = root.findall(".//ex:invention-title", ns)
    for t in titles:
        lang = t.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
        if lang == "en":
            data["title"] = t.text
            break

    if not data["title"] and titles:
        data["title"] = titles[0].text

    # Nettoyage des noms (suppression des espaces doubles et caractères bizarres)
    for a in root.findall(".//ex:applicant//ex:name", ns):
        if a.text:
            name = " ".join(a.text.split())
            if name not in data["applicants"]:
                data["applicants"].append(name)

    for i in root.findall(".//ex:inventor//ex:name", ns):
        if i.text:
            name = " ".join(i.text.split())
            if name not in data["inventors"]:
                data["inventors"].append(name)

    for c in root.findall(".//ex:classification-ipcr/ex:text", ns):
        data["cpc"].append(c.text.strip())

    return data


def parse_abstract(xml_text):
    if not xml_text:
        return None

    ns = {"ex": "http://www.epo.org/exchange"}
    root = ET.fromstring(xml_text)

    paragraphs = [p.text for p in root.findall(".//ex:abstract//ex:p", ns) if p.text]
    return " ".join(paragraphs) if paragraphs else None


# -------------------------
# Cœur du Crawler Intégré
# -------------------------
total_db_count = 0
nb_ecrits_jsonl = 0

with open(output_path, "a", encoding="utf-8") as out:
    for query in QUERIES:
        start = 1
        query_db_count = 0

        while query_db_count < MAX_RECORDS_DB:
            end = start + STEP - 1
            print(f"[INFO] Requête OPS {start}-{end} pour : {query}")

            try:
                xml = fetcher.search(query=query, start=start, end=end)
                refs = extract_publication_references(xml)

                if not refs:
                    print(f"[INFO] Fin des résultats pour la requête : {query}")
                    break

                for ref in refs:
                    docdb_id = ref["docdb_id"]

                    # Saut si déjà dans le fichier JSONL (déjà traité lors d'un run précédent)
                    if docdb_id in existing_docdb_ids:
                        continue

                    try:
                        # 1. Enrichissement via API
                        biblio_xml = fetcher.get_biblio_docdb(docdb_id)
                        if not biblio_xml:
                            continue

                        abstract_xml = fetcher.get_abstract_docdb(docdb_id)
                        biblio_data = parse_biblio(biblio_xml)
                        abstract = parse_abstract(abstract_xml)

                        # 2. Construction du Record
                        record = {
                            "source": "EPO OPS",
                            "family_id": ref["family_id"],
                            "docdb_id": docdb_id,
                            "kind": ref.get("kind"),
                            **biblio_data,
                            "abstract": abstract,
                        }
                        print(
                            f"   [+] Traitement brevet : {docdb_id} - {biblio_data['title'][:50]}..."
                        )

                        # 3. Écriture JSONL (Visualisation limitée)

                        if nb_ecrits_jsonl < MAX_RECORDS_JSON:
                            try:
                                line = json.dumps(record, ensure_ascii=False) + "\n"
                                out.write(line)
                                out.flush()  # Force l'apparition dans le fichier immédiatement
                                nb_ecrits_jsonl += 1
                            except Exception as e:
                                print(f"Erreur écriture fichier : {e}")

                        # 4. Create authors in database (applicants and inventors)
                        author_ids = []
                        all_authors = (
                            biblio_data["applicants"] + biblio_data["inventors"]
                        )

                        for idx, author_name in enumerate(all_authors):
                            roles = []
                            if idx < len(biblio_data["applicants"]):
                                roles.append("applicant")
                            if idx >= len(biblio_data["applicants"]):
                                roles.append("inventor")

                            author_create = AuthorCreate(
                                full_name=author_name,
                                external_id=f"epo_{docdb_id}_{idx}",
                                roles=roles,
                            )
                            author = author_service.create(session, author_create)
                            author_ids.append(author.id)

                        # 5. Insertion Base de Données (SQLModel)
                        research_item = ResearchItemCreate(
                            source_id=epo_source.id,
                            external_id=docdb_id,
                            doi=None,
                            title=biblio_data["title"],
                            year=int(ref["doc_number"][:4])
                            if ref["doc_number"][:4].isdigit()
                            else None,
                            type="patent",
                            metrics={
                                "author_ids": author_ids,
                                "kind": ref.get("kind"),
                                "authors": all_authors,
                                "organizations": {
                                    "names": biblio_data["applicants"],
                                    "countries": [ref["country"]],
                                },
                            },
                            raw=record,
                        )

                        try:
                            item_service.create(session, research_item)
                            session.commit()
                            query_db_count += 1
                            total_db_count += 1
                        except IntegrityError:
                            session.rollback()
                        except Exception as e:
                            session.rollback()
                            print(f"[ERREUR DB] {e}")

                        existing_docdb_ids.add(docdb_id)
                        time.sleep(1.5)  # Throttling strict

                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 403:
                            print("[ALERTE] 403 Quota. Pause 30s...")
                            time.sleep(30)
                            continue

                    if query_db_count >= MAX_RECORDS_DB:
                        break

                start += STEP
                time.sleep(1)  # Pause entre les pages

            except Exception as e:
                print(f"[ERREUR] {e}")
                break

print(f"[INFO] Terminé. Total inséré en DB : {total_db_count}")
