"""
USAGE:
Commencer par lancer le serveur:
    uv run uvicorn main:app --reload

    Puis:
    uv run python -m crawlers.Hal_Bulk_Publications

    => va générer un fichier 'hal_publications.jsonl' dans /data/
    => va enregistrer les lignes dans la database.db
 
QUERY: 'intelligence artificielle' + "artificial intelligence" from 2019

EXPLICATIONS
    Fonctionne en complément avec Hal_fetcher_publications.py
    Logique métier + écriture fichier

OBSERVATIONS:
    Il n'y a pas de données country renseignées sur HAL - l'exemple exposé ci-dessous doit être une exception
    voir: https://api.archives-ouvertes.fr/search/?q=intelligence%20artificielle&rows=1&fl=*&wt=json pour obtenir les noms des champs
"""
# Imports de base pour le crawler => fichier jsonl
import json
from .Hal_fetcher_publications import HALPublicationFetcher
from pathlib import Path

# Imports nécessaires pour insertion dans la base de donnée
from database import get_session
from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate


# Initialisation des services et création des réfs HAL pour future insertion
source_service = SourceService()
item_service = ResearchItemService()

session = next(get_session())

hal = source_service.create(
    session,
    SourceCreate(
        name="hal",
        type="academic",
        base_url="https://api.archives-ouvertes.fr/"
    )
)


# QUERY:
QUERIES = [
    '"intelligence artificielle"',
    '"artificial intelligence"',
]
START_YEAR = 2019
MAX_RECORDS = 10_000


Path("data").mkdir(parents=True, exist_ok=True)
fetcher = HALPublicationFetcher()



# Ecriture dans le jsonl:
with open("data/hal_publications.jsonl", "a", encoding="utf-8") as f:
    
    for query in QUERIES:
        start = 0
        count = 0
    
        while count < MAX_RECORDS:
            docs = fetcher.fetch(query, START_YEAR, start=start)
            if not docs:
                break

            for doc in docs:
                
                # --- A. Écriture JSONL ---
                '''
                record = {
                    "source": "HAL",
                    "query": query,
                    "publication": {
                        "id": doc.get("halId_s"),
                        "title": doc.get("title_s"),
                        "year": doc.get("producedDateY_i"),
                        "doi": doc.get("doiId_s"),
                        "domains": doc.get("domain_s", []),
                        "keywords": doc.get("keyword_s", []),
                    },
                    "authors": doc.get("authFullName_s", [])
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                '''

                # --- B. Insertion DB ---

                raw_title = doc.get("title_s")
                if isinstance(raw_title, list):
                    title = raw_title[0] if raw_title else None
                else:
                    title = raw_title

                research_item = ResearchItemCreate(
                    source_id=hal.id,
                    external_id=doc.get("halId_s"),
                    type="article",
                    title=title,
                    year=doc.get("producedDateY_i"),
                    is_retracted=False,
                    is_open_access=None,
                    metrics={
                        "domains": doc.get("domain_s", []),
                        "keywords": doc.get("keyword_s", []),
                        "authors": doc.get("authFullName_s", []),
                        "query": query
                    },
                    raw=doc
                )

                # --- Gestion des doublons ---
                try:
                    item_service.create(session, research_item)
                except Exception:
                    pass
                
                # Max 'par requête' 
                count += 1
                if count >= MAX_RECORDS:
                    break

            start += fetcher.rows
            print(f"{count} notices collectées…", end="\r")
    print(f"\nRequête terminée : {query}")
print("\nTéléchargement terminé.")