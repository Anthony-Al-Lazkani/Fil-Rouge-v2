"""
Crawler OpenCorporates

Limitations Techniques :
- API Key : Requiert un jeton API (stocké dans .env) pour dépasser les quotas publics.

Variables de contrôle (Pilotables via le pipeline) :
- limit : Nombre total d'entreprises à récupérer (max 100 par appel standard).
- query : Mot-clé de recherche (par défaut "artificial intelligence").
"""

import os
import time
import requests
from dotenv import load_dotenv
from typing import List, Dict, Any

# CONFIG POC
load_dotenv()

MAX_RECORDS = 10000
SEARCH_QUERY = "machine learning"
JURISDICTION = None  # None = search all jurisdictions


"""
Fonctionnement
    1. Initialise les paramètres de requête en utilisant la clé API du fichier .env.
    2. Bride la demande à 100 résultats maximum (limite technique du paramètre per_page).
    3. Récupère le flux JSON et extrait les objets imbriqués dans results -> companies.
    4. Filtre les entrées invalides et construit un dictionnaire normalisé pour le processeur.
    5. Interrompt l'accumulation dès que le quota 'limit' est atteint.
"""
def crawl_opencorporates_ai(limit: int = MAX_RECORDS, query: str = SEARCH_QUERY) -> List[Dict[str, Any]]:
    api_key = os.getenv("OPENCORPORATES_API_KEY") #1.
    base_url = "https://api.opencorporates.com/v0.4/companies/search"

    all_companies = []
    current_page = 1 

    print(f"=== Crawling OpenCorporates POC (Query: {query} | Limit: {limit}) ===")

    while len(all_companies) < limit:
        params = {
            "q": query, 
            "api_token": api_key, 
            "per_page": 100, #2.
            "page": current_page 
        }

        try: 
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", {}).get("companies", [])

            if not results: 
                break

            for item in results:
                if len(all_companies) >= limit:
                    break
                    
                co = item.get("company")
                if not co: continue

                company_data = {
                    "external_id": co.get("company_number"),
                    "name": co.get("name"),
                    "type": co.get("company_type"),
                    "jurisdiction": co.get("jurisdiction_code"),
                    "founded_date": co.get("incorporation_date"),
                    "operating_status": co.get("current_status"),
                    "raw": co,
                }
                all_companies.append(company_data)

            print(f"Page {current_page} récupérée ({len(all_companies)}/{limit})")
            current_page += 1 # On passe à la page suivante
            

        except Exception as e:
            print(f"[ERROR] OpenCorporates crawl failed at page {current_page}: {e}")
            break

    print(f"Done. Collected {len(all_companies)} companies for POC.")
    return all_companies
