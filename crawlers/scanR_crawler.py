import requests
import time
from typing import List, Dict, Any

# La nouvelle URL identifiée via l'inspecteur réseau
BASE_URL = "https://scanr.enseignementsup-recherche.gouv.fr/api/scanr-organizations/_search"

def crawl_scanr_ai(query: str = "intelligence artificielle", max_pages: int = 6) -> List[Dict[str, Any]]:
    all_results = []
    
    # Payload standard pour Elasticsearch utilisé par ScanR
    payload = {
        "query": {
            "query_string": {
                "query": query,
                "default_operator": "AND"
            }
        },
        "size": 20,
        "from": 0  # La pagination Elasticsearch utilise 'from' au lieu de 'page'
    }

    print(f"=== Crawling ScanR for: {query} ===")

    for page in range(max_pages):
        payload["from"] = page * payload["size"]
        
        try:
            response = requests.post(BASE_URL, json=payload)
            
            if response.status_code != 200:
                print(f"Erreur {response.status_code}: {response.text}")
                break
                
            data = response.json()
            
            # Dans Elasticsearch, les résultats sont dans hits -> hits
            hits = data.get("hits", {}).get("hits", [])
            
            if not hits:
                print("Fin des résultats.")
                break

            for hit in hits:
                source = hit.get("_source", {})
                
                # Extraction des industries (Domaines ERC ou mots-clés)
                domains = [d.get("label", {}).get("default") for d in source.get("domains", []) if d.get("label")]
                
                # Extraction de la date de création
                creation_year = source.get("creationYear")
                
                org_data = {
                    "external_id": source.get("id"),
                    "name": source.get("label", {}).get("default") or source.get("label", {}).get("fr", "Sans nom"),
                    "type": source.get("kind", ["organization"])[0] if isinstance(source.get("kind"), list) else source.get("kind"),
                    "country": "France",
                    "city": source.get("address", [{}])[0].get("city") if source.get("address") else None,
                    "description": source.get("description", {}).get("default"),
                    "website": source.get("links", [{}])[0].get("url") if source.get("links") else None,
                    "founded_date": str(creation_year) if creation_year else None,
                    "operating_status": source.get("status"),
                    "industries": domains,
                    "is_ai_related": True,
                    "raw": source  # On insère tout l'objet ici pour ne rien perdre
                }
                all_results.append(org_data)
           
            print(f"Collecté {len(all_results)} organisations...", end="\r")
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Request failed: {e}")
            break

    print(f"\nTerminé. {len(all_results)} organisations récupérées.")
    return all_results