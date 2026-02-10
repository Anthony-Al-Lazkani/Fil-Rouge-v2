'''
Penser à aller autoriser mon application sur: (dure 20 minutes)
https://developers.epo.org/user/31706/app-detail/ed3afe02-dce8-47ef-a214-fd5a96a82652

Ce script constitue le module principal d’extraction et d’enrichissement
des données brevets issues de l’API EPO OPS (European Patent Office –
Open Patent Services), dans le cadre du projet Fil Rouge.

Objectif général
----------------
Interroger de manière incrémentale et robuste l’API EPO OPS afin de :
- rechercher des brevets correspondant à une requête CQL donnée,
- extraire les identifiants de publication de type DOCDB,
- enrichir chaque publication avec ses métadonnées bibliographiques
  (biblio) et son résumé (abstract),
- stocker les résultats sous forme de lignes JSON (format JSONL),
  exploitables ultérieurement pour des traitements de type analyse,
  indexation ou graphe de connaissances.

Fonctionnement général
----------------------
Le script fonctionne selon une logique de pagination contrôlée, imposée
par les contraintes de l’API EPO OPS :

1. La recherche est effectuée par blocs successifs (Range 1–100, 101–200,
   etc.), afin de respecter les limites de requêtes.
2. À chaque itération :
   - les références de publication sont extraites depuis la réponse XML
     du endpoint /published-data/search ;
   - les identifiants DOCDB (country + doc-number) sont construits ;
   - les publications déjà présentes dans le fichier de sortie sont
     ignorées afin d’éviter les doublons ;
   - les endpoints /biblio et /abstract sont appelés pour enrichir les
     données.
3. Les résultats sont ajoutés progressivement (append) dans un fichier
   JSONL unique, permettant une reprise ultérieure du script sans perte
   de données.

Contraintes et précautions
--------------------------
- Le script respecte les quotas de l’API OPS en introduisant des pauses
  entre les requêtes et entre les pages de résultats.
- Les erreurs HTTP (403, 404, etc.) peuvent survenir en cas de dépassement
  de quota ou de documents non accessibles ; le script est conçu pour
  pouvoir être relancé après interruption.
- Le format JSONL garantit une écriture incrémentale et une compatibilité
  avec les autres sources du projet (ArXiv, HAL, Crunchbase).

Responsabilités
---------------
Ce script assure exclusivement :
- la logique de collecte,
- la gestion de la pagination,
- l’enrichissement des données brevets,
- la persistance incrémentale des résultats.

Il ne réalise aucun traitement analytique ou sémantique avancé, ces
traitements étant destinés à être effectués dans des modules ultérieurs
du projet Fil Rouge.
'''


from .Inpi_fetcher import InpiFetcher
import xml.etree.ElementTree as ET
import requests
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import os
from sqlalchemy.exc import IntegrityError

# -------------------------
# Initialisation
# -------------------------

load_dotenv()

fetcher = InpiFetcher(
    os.getenv("EPO_CLIENT_ID"),
    os.getenv("EPO_CLIENT_SECRET"),
)

Path("data").mkdir(exist_ok=True)


# --- CONFIGURATION ---
QUERIES = ['ti="artificial intelligence"', 'ti="intelligence artificielle"']
MAX_RECORDS_DB = 10_000
MAX_RECORDS_JSON = 100



# -------------------------
# Étape 2 : extraction des pointeurs
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

        results.append({
            "family_id": family_id,
            "docdb_id": f"{country}{doc_number}",
            "country": country,
            "doc_number": doc_number,
            "kind": kind,
        })

    return results

# -------------------------
# Étape 3 : parsing ciblé
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

    paragraphs = [
        p.text for p in root.findall(".//ex:abstract//ex:p", ns)
        if p.text
    ]
    return " ".join(paragraphs) if paragraphs else None


# ----------------------
# Boucle itérative pour ne pas requêter à la main
# ---------------------------

output_path = Path("data/epo_ai_brevets.jsonl")
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

print(f"[INFO] Brevets déjà présents : {len(existing_docdb_ids)}")


# ---------------------
# Coeur du crawler
# ----------------------

QUERY = "ti=artificial intelligence"
STEP = 100
start = 1

with open(output_path, "a", encoding="utf-8") as out:
    while True:
        end = start + STEP - 1
        print(f"[INFO] Requête OPS {start}-{end}")

        xml = fetcher.search(
            query=QUERY,
            start=start,
            end=end,
        )

        refs = extract_publication_references(xml)

        if not refs:
            print("[INFO] Plus aucun résultat, arrêt.")
            break

        print(f"[INFO] {len(refs)} références trouvées")

        for ref in refs:
            docdb_id = ref["docdb_id"]

            if docdb_id in existing_docdb_ids:
                continue

            try:
                # Récupération des données XML
                biblio_xml = fetcher.get_biblio_docdb(docdb_id)
                if not biblio_xml:
                    continue
                
                abstract_xml = fetcher.get_abstract_docdb(docdb_id)

                # Construction du dictionnaire (à l'intérieur du try)
                record = {
                    "source": "EPO OPS",
                    "family_id": ref["family_id"],
                    "docdb_id": docdb_id,
                    "kind": ref.get("kind"),
                    **parse_biblio(biblio_xml),
                    "abstract": parse_abstract(abstract_xml),
                }

                # Écriture (à l'intérieur du try)
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                existing_docdb_ids.add(docdb_id)

                # Pause préventive pour le throttling
                time.sleep(1.5)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    print(f"[ALERTE] Quota atteint ou accès refusé pour {docdb_id}. Pause de 30 secondes...")
                    time.sleep(30)
                    continue 
                else:
                    print(f"[ERREUR HTTP] {e}")
                    continue
            except Exception as e:
                print(f"[ERREUR INATTENDUE] {e}")
                continue

        start += STEP
        time.sleep(1)

print("[INFO] Terminé.")