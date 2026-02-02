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

# Initialisation des services
source_service = SourceService()
item_service = ResearchItemService()
session = next(get_session())

# Création de la source HAL
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
MAX_RECORDS = 10_000

Path("data").mkdir(parents=True, exist_ok=True)
fetcher = HALPublicationFetcher()

# EXECUTION
with open("data/hal_publications.jsonl", "w", encoding="utf-8") as f:
    
    for query in QUERIES:
        start = 0
        count = 0
    
        while count < MAX_RECORDS:
            docs = fetcher.fetch(query, START_YEAR, start=start)
            if not docs:
                break

            for doc in docs:
                # --- 1. Préparation et nettoyage des données ---
                raw_title = doc.get("title_s")
                title = raw_title[0] if isinstance(raw_title, list) and raw_title else raw_title
                
                # Récupération des champs validés par nos tests API
                doi = doc.get("doiId_s") # Champ désormais validé
                doc_type = doc.get("docType_s")
                
                # Utilisation des champs d'affiliation des auteurs (plus précis)
                struct_ids = doc.get("authStructId_i", [])
                struct_names = doc.get("authStructName_s", [])
                struct_types = doc.get("authStructType_s", [])
                struct_countries = doc.get("authStructCountry_s", [])

                # --- 2. Écriture dans le fichier JSONL ---
                record = {
                    "source": "HAL",
                    "query": query,
                    "publication": {
                        "id": doc.get("halId_s"),
                        "doi": doi,
                        "type": doc_type,
                        "title": title,
                        "year": doc.get("producedDateY_i"),
                        "domains": doc.get("domain_s", []),
                        "keywords": doc.get("keyword_s", []),
                    },
                    "authors": doc.get("authFullName_s", []),
                    "organizations": {
                        "ids": struct_ids,
                        "names": struct_names,
                        "types": struct_types,
                        "countries": struct_countries
                    }
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

                # --- 3. Insertion dans la Base de Données ---
                research_item = ResearchItemCreate(
                    source_id=hal.id,
                    external_id=doc.get("halId_s"),
                    type=doc_type or "article",
                    title=title,
                    year=doc.get("producedDateY_i"),
                    is_retracted=False,
                    is_open_access=None,
                    metrics={
                        "doi": doi, # Ajout du DOI dans les métriques
                        "domains": doc.get("domain_s", []),
                        "keywords": doc.get("keyword_s", []),
                        "authors": doc.get("authFullName_s", []),
                        "query": query,
                        "organizations": {
                            "names": struct_names,
                            "types": struct_types, # Crucial pour filtrer les "company"
                            "countries": struct_countries
                        }
                    },
                    raw=doc # Contient l'intégralité de la réponse API pour archive
                )

                try:
                    item_service.create(session, research_item)
                except Exception:
                    # En cas de doublon ou d'erreur, on passe au suivant
                    pass
                
                count += 1
                if count >= MAX_RECORDS:
                    break

            start += fetcher.rows
            print(f"{count} notices collectées pour la requête : {query}", end="\r")
            
    print(f"\nRequêtes terminées.")
print("Téléchargement et synchronisation BDD terminés.")