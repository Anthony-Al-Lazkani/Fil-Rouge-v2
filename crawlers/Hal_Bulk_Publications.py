"""
USAGE:
Commencer par lancer le serveur:
    uv run uvicorn main:app --reload

    Puis:
    uv run python -m crawlers.Hal_Bulk_Publications

    => va générer un fichier 'hal_publications.jsonl' dans /data/
    => va enregistrer les lignes dans la database.db
 
QUERY: 'intelligence artificielle' + "artificial intelligence" from 2021

EXPLICATIONS
    Fonctionne en complément avec Hal_fetcher_publications.py
    Logique métier + écriture fichier

OBSERVATIONS:
    Il n'y a pas de données country renseignées sur HAL - l'exemple exposé ci-dessous doit être une exception
    voir: https://api.archives-ouvertes.fr/docs/search/?schema=fields#fields pour obtenir les noms des champs
"""



# Imports de base pour le crawler => fichier jsonl
import json
from .Hal_fetcher_publications import HALPublicationFetcher
from pathlib import Path

# Imports nécessaires pour la base de données
from database import get_session, engine
from models.research_item import ResearchItem # Importez vos modèles
from models.source import Source
from sqlalchemy import delete

from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate

# Initialisation des services
source_service = SourceService()
item_service = ResearchItemService()
session = next(get_session())


# --- ÉTAPE 0 : NETTOYAGE DE LA BASE DE DONNÉES ---
print("Nettoyage de la base de données en cours...")
try:
    # On vide la table des items pour repartir de zéro
    session.execute(delete(ResearchItem))
    session.commit()
    print("Base de données réinitialisée.")
except Exception as e:
    session.rollback()
    print(f"Erreur lors du nettoyage : {e}")



# Création de la source HAL (ou récupération si elle existe encore)
hal = source_service.create(
    session,
    SourceCreate(
        name="hal",
        type="academic",
        base_url="https://api.archives-ouvertes.fr/"
    )
)

# CONFIGURATION
QUERIES = [
    '"intelligence artificielle"',
    '"artificial intelligence"',
]
START_YEAR = 2021
MAX_RECORDS_DB = 10_000 # Limite pour l'insertion dans la BDD
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
                title = raw_title[0] if isinstance(raw_title, list) and raw_title else raw_title
                
                '''
                # Récupération des identifiants
                doi = doc.get("doiId_s")
                doc_type = doc.get("docType_s")

                # Récupération des organisations (champs globaux pour garantir la complétude)
                # Nous utilisons à nouveau structId_i et ses dérivés qui fonctionnaient
                struct_ids = doc.get("structId_i", [])
                struct_names = doc.get("structName_s", [])
                struct_types = doc.get("structType_s", [])
                struct_countries = doc.get("structCountry_s", [])
                '''

                # --- 2. Écriture JSONL ---
                if count < MAX_RECORDS_JSON:
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
                        "authors": doc.get("authFullName_s", []),
                        "organizations": {
                            "ids": doc.get("structId_i", []),
                            "names": doc.get("structName_s", []),
                            "types": doc.get("structType_s", []),
                            "countries": doc.get("structCountry_s", [])
                        }
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

                # --- 3. Insertion DB ---
                research_item = ResearchItemCreate(
                    source_id=hal.id,
                    external_id=doc.get("halId_s"),
                    type=doc.get("docType_s") or "article",
                    title=title,
                    year=doc.get("producedDateY_i"),
                    is_retracted=False,
                    metrics={
                        "doi": doc.get("doiId_s"),                       
                        "domains": doc.get("domain_s", []),
                        "keywords": doc.get("keyword_s", []),
                        "authors": doc.get("authFullName_s", []),
                        "query": query,
                        "organizations": {
                            "names": doc.get("structName_s", []),
                            "types": doc.get("structType_s", []),
                            "countries": doc.get("structCountry_s", []),
                        }
                    },
                    raw=doc
                )

                try:
                    item_service.create(session, research_item)
                except Exception:
                    pass
                
                count += 1
                if count >= MAX_RECORDS_DB:
                    break

            start += fetcher.rows
            print(f"{count} notices collectées pour {query}…", end="\r")
            
    print(f"\nRequêtes terminées.")
print("Téléchargement et synchronisation BDD terminés.")