"""
USAGE:
Commencer par lancer le serveur:
    uv run uvicorn main:app --reload

    Puis:
    uv run python -m crawlers.Hal_Bulk_Publications

    => va générer un fichier 'hal_publications.jsonl' dans /data/
    => va enregistrer les lignes dans la database.db

QUERY: 'intelligence artificielle' + "artificial intelligence" from 2021 => environ 10 000 articles

EXPLICATIONS
    Fonctionne en complément avec Hal_fetcher_publications.py
    Logique métier + écriture fichier
    Va récupérer les articles et les intégrer dans la table "RESEARCH_ITEM" de la database.db
    On génère un json pour visualiser les données mais on ne fait que les 100 premiers, tout le reste va bien dans la database

OBSERVATIONS:
    Il n'y a pas de données country renseignées sur HAL - l'exemple exposé ci-dessous doit être une exception
    voir: https://api.archives-ouvertes.fr/docs/search/?schema=fields#fields pour obtenir les noms des champs
"""

# Imports de base pour le crawler => fichier jsonl
import json
from .Hal_fetcher_publications import HALPublicationFetcher
from pathlib import Path

# Imports nécessaires pour la base de données
from database import get_session
from sqlalchemy.exc import IntegrityError

from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate

# Initialisation des services
source_service = SourceService()
item_service = ResearchItemService()
session = next(get_session())


# Création de la source HAL (ou récupération si elle existe encore)
hal = source_service.create(
    session,
    SourceCreate(
        name="hal", type="academic", base_url="https://api.archives-ouvertes.fr/"
    ),
)

# CONFIGURATION
QUERIES = [
    '"intelligence artificielle"',
    '"artificial intelligence"',
]
START_YEAR = 2020
MAX_RECORDS_DB = 10_000  # Limite pour l'insertion dans la BDD
MAX_RECORDS_JSON = 100  # Limite pour la visualisation

Path("data").mkdir(parents=True, exist_ok=True)
fetcher = HALPublicationFetcher(rows=500)

# EXECUTION
print(f"Lancement de la collecte exhaustive depuis {START_YEAR}...")

with open("data/hal_publications.jsonl", "w", encoding="utf-8") as f:
    for query in QUERIES:
        start = 0
        count = 0
        while count < MAX_RECORDS_DB:
            docs = fetcher.fetch(query, START_YEAR, start=start)
            if not docs:
                break

            for doc in docs:
                # 1. Extraction des données
                raw_title = doc.get("title_s")
                title = (
                    raw_title[0]
                    if isinstance(raw_title, list) and raw_title
                    else raw_title
                )

                """
                # Récupération des identifiants
                doi = doc.get("doiId_s")
                doc_type = doc.get("docType_s")

                # Récupération des organisations (champs globaux pour garantir la complétude)
                # Nous utilisons à nouveau structId_i et ses dérivés qui fonctionnaient
                struct_ids = doc.get("structId_i", [])
                struct_names = doc.get("structName_s", [])
                struct_types = doc.get("structType_s", [])
                struct_countries = doc.get("structCountry_s", [])
                """

                # --- 2. Écriture JSONL ---
                if count < MAX_RECORDS_JSON:
                    # Build authors with organization info
                    authors_raw = doc.get("authFullName_s", [])
                    struct_ids = doc.get("structId_i", [])
                    struct_names = doc.get("structName_s", [])
                    struct_types = doc.get("structType_s", [])
                    struct_countries = doc.get("structCountry_s", [])

                    # Build author list with affiliations
                    authors_list = []
                    for idx, name in enumerate(authors_raw):
                        author_entry = {
                            "display_name": name,
                            "roles": ["first_author"] if idx == 0 else ["co_author"],
                            "affiliations": [],
                        }
                        # Add affiliation info if available
                        if idx < len(struct_names):
                            author_entry["affiliations"].append(
                                {
                                    "id": struct_ids[idx]
                                    if idx < len(struct_ids)
                                    else None,
                                    "display_name": struct_names[idx],
                                    "type": struct_types[idx]
                                    if idx < len(struct_types)
                                    else None,
                                    "country_code": struct_countries[idx]
                                    if idx < len(struct_countries)
                                    else None,
                                }
                            )
                        authors_list.append(author_entry)

                    record = {
                        "source": "HAL",
                        "query": query,
                        "publication": {
                            "id": doc.get("halId_s"),
                            "doi": doc.get("doiId_s"),
                            "type": doc.get("docType_s"),
                            "title": title,
                            "year": doc.get("producedDateY_i"),
                            "domains": doc.get("domain_s", []),
                            "keywords": doc.get("keyword_s", []),
                        },
                        "authors": authors_list,
                        "organizations": {
                            "ids": doc.get("structId_i", []),
                            "names": doc.get("structName_s", []),
                            "types": doc.get("structType_s", []),
                            "countries": doc.get("structCountry_s", []),
                        },
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

                # --- 3. Insertion DB ---
                # Build authors with affiliations
                authors_raw = doc.get("authFullName_s", [])
                struct_ids = doc.get("structId_i", [])
                struct_names = doc.get("structName_s", [])
                struct_types = doc.get("structType_s", [])
                struct_countries = doc.get("structCountry_s", [])

                authors_for_db = []
                for idx, name in enumerate(authors_raw):
                    author_entry = {
                        "display_name": name,
                        "roles": ["first_author"] if idx == 0 else ["co_author"],
                        "affiliations": [],
                    }
                    if idx < len(struct_names):
                        author_entry["affiliations"].append(
                            {
                                "id": struct_ids[idx]
                                if idx < len(struct_ids)
                                else None,
                                "display_name": struct_names[idx],
                                "type": struct_types[idx]
                                if idx < len(struct_types)
                                else None,
                                "country_code": struct_countries[idx]
                                if idx < len(struct_countries)
                                else None,
                            }
                        )
                    authors_for_db.append(author_entry)

                research_item = ResearchItemCreate(
                    source_id=hal.id,
                    external_id=doc.get("halId_s"),
                    doi=doc.get("doiId_s"),
                    type=doc.get("docType_s") or "article",
                    title=title,
                    year=doc.get("producedDateY_i"),
                    abstract=None,  # HAL API doesn't provide abstract in basic search
                    language=None,  # Could be inferred from title/text
                    is_retracted=False,
                    is_open_access=True,  # HAL is open access by default
                    license="CC-BY" if doc.get("license_s") else None,
                    url=f"https://hal.science/hal-{doc.get('halId_s')}"
                    if doc.get("halId_s")
                    else None,
                    citation_count=0,  # HAL doesn't provide citation count in basic search
                    keywords=doc.get("keyword_s", []),
                    topics=doc.get("domain_s", []),
                    metrics={
                        "doi": doc.get("doiId_s"),
                        "domains": doc.get("domain_s", []),
                        "keywords": doc.get("keyword_s", []),
                        "authors": authors_for_db,
                        "query": query,
                        "organizations": {
                            "ids": doc.get("structId_i", []),
                            "names": doc.get("structName_s", []),
                            "types": doc.get("structType_s", []),
                            "countries": doc.get("structCountry_s", []),
                        },
                    },
                    raw=doc,
                )

                try:
                    item_service.create(session, research_item)
                except IntegrityError:
                    # C'est un doublon (DOI déjà présent)
                    session.rollback()
                    # On passe silencieusement au suivant
                except Exception as e:
                    # C'est une autre erreur (problème réseau, structure, etc.)
                    session.rollback()
                    print(f"Erreur inattendue : {e}")

                count += 1
                if count >= MAX_RECORDS_DB:
                    break

            start += fetcher.rows
            print(f"{count} notices collectées pour {query}…", end="\r")

    print(f"\nRequêtes terminées.")
print("Téléchargement et synchronisation BDD terminés.")
