import requests
import time
from typing import List, Dict, Any

BASE_URL = "https://scanr.enseignementsup-recherche.gouv.fr/api/scanr-organizations/_search"

def crawl_scanr_ai(query: str = "intelligence artificielle", limit: int = 30) -> List[Dict[str, Any]]:
    all_results = []
    payload = {
        "query": {
            "query_string": {
                "query": query,
                "default_operator": "AND"
            }
        },
        "size": limit,
        "from": 0
    }

    print(f"=== Crawling ScanR for: {query} ===")
    try:
        response = requests.post(BASE_URL, json=payload)
        response.raise_for_status()
        hits = response.json().get("hits", {}).get("hits", [])

        for hit in hits:
            source = hit.get("_source", {})
            # Identification du SIREN (priorité aux IDs externes de type siren)
            siren = next((item.get("id") for item in source.get("externalIds", []) if item.get("type") == "siren"), source.get("id"))
            
            all_results.append({
                "external_id": siren,
                "name": source.get("label", {}).get("default") or "Sans nom",
                "type": "company" if source.get("kind", []) == ["Company"] else "facility",
                "city": source.get("address", [{}])[0].get("city") if source.get("address") else None,
                "founded_date": str(source.get("creationYear")) if source.get("creationYear") else None,
                "operating_status": source.get("status"),
                "is_ai_related": True,
                "raw": source 
            })
    except Exception as e:
        print(f"[ERROR] ScanR request failed: {e}")

    return all_results