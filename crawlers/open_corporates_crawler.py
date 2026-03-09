import os
import requests
import time
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

def crawl_opencorporates_ai(limit: int = 5) -> List[Dict[str, Any]]:
    api_key = os.getenv("OPENCORPORATES_API_KEY")
    search_url = "https://api.opencorporates.com/v0.4/companies/search"
    
    params = {
        "q": "intelligence artificielle",
        "jurisdiction_code": "fr",
        "api_token": api_key,
        "per_page": limit
    }

    detailed_results = []
    try:
        print(f"[*] Recherche initiale via /search...")
        resp = requests.get(search_url, params=params)
        resp.raise_for_status()
        search_results = resp.json().get("results", {}).get("companies", [])
        print(f"[+] {len(search_results)} entreprises trouvées. Début de l'enrichissement...")

        for item in search_results:
            co = item.get("company")
            if not co: continue
            
            # Appel détaillé
            jur = co['jurisdiction_code']
            num = co['company_number']
            detail_url = f"https://api.opencorporates.com/v0.4/companies/{jur}/{num}"
            
            try:
                print(f"    -> Enrichissement : {co['name']} ({num})")
                d_resp = requests.get(detail_url, params={"api_token": api_key})
                if d_resp.status_code == 200:
                    full_data = d_resp.json().get("results", {}).get("company")
                    if full_data:
                        detailed_results.append(full_data)
                else:
                    print(f"    [!] Échec détail (Code: {d_resp.status_code})")
            except Exception as e:
                print(f"    [!] Erreur sur {num}: {e}")
            
            time.sleep(0.5) # Crucial pour ne pas se faire bannir

    except Exception as e:
        print(f"[ERROR] Crawler crash: {e}")
        return []

    print(f"[*] Crawler terminé. {len(detailed_results)} fiches complètes prêtes.")
    return detailed_results