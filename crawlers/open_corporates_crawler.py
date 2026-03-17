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

MAX_RECORDS = 100
SEARCH_QUERY = "artificial intelligence"
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
    api_key = os.getenv("OPENCORPORATES_API_KEY") # 1.
    base_url = "https://api.opencorporates.com/v0.4/companies/search"

    all_companies = []

    params = {
        "q": SEARCH_QUERY, 
        "api_token": api_key, 
        "per_page": min(limit, 100) #2.
        }


    print(f"=== Crawling OpenCorporates POC (Query: {query} | Limit: {limit}) ===")

    try: 
        response = requests.get(base_url, params=params)
        response.raise_for_status()

        results = response.json().get("results", {}).get("companies", []) # 3.

        for item in results:
            if len(all_companies) >= limit:
                break
                
            co = item.get("company")
            if not co:
                continue

            # On construit la structure de donnée propre 4.
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

            if len(all_companies) >= MAX_RECORDS: # 5.
                break

    except Exception as e:
        print(f"[ERROR] OpenCorporates crawl failed: {e}")

    print(f"Done. Collected {len(all_companies)} companies for POC.")
    return all_companies
