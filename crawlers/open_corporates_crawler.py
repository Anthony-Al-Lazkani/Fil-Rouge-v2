import os
import time
import requests
from dotenv import load_dotenv
from typing import List, Dict, Any

# CONFIG POC
load_dotenv()

MAX_POC_RECORDS = 10
SEARCH_QUERY = "intelligence artificielle"
JURISDICTION = "fr"

def crawl_opencorporates_ai() -> List[Dict[str, Any]]:
    api_key = os.getenv("OPENCORPORATES_API_KEY")
    base_url = "https://api.opencorporates.com/v0.4/companies/search"
    
    all_companies = []
    
    params = {
        "q": SEARCH_QUERY,
        "jurisdiction_code": JURISDICTION,
        "api_token": api_key,
        "per_page": MAX_POC_RECORDS 
    }

    print(f"=== Crawling OpenCorporates POC (Query: {SEARCH_QUERY}) ===")

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        results = response.json().get("results", {}).get("companies", [])
        
        for item in results:
            co = item.get("company")
            if not co:
                continue
                
            # On construit la structure de donnée propre
            company_data = {
                "external_id": co.get("company_number"),
                "name": co.get("name"),
                "type": co.get("company_type"),
                "jurisdiction": co.get("jurisdiction_code"),
                "founded_date": co.get("incorporation_date"),
                "operating_status": co.get("current_status"),
                "raw": co
            }
            all_companies.append(company_data)
            
            if len(all_companies) >= MAX_POC_RECORDS:
                break

    except Exception as e:
        print(f"[ERROR] OpenCorporates crawl failed: {e}")

    print(f"Done. Collected {len(all_companies)} companies for POC.")
    return all_companies