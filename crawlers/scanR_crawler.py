import requests
import time
import json
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
                
            # --- FIX ENCODAGE ICI ---
            # Au lieu de response.json(), on récupère le texte brut et on le décode proprement
            raw_text = response.text
            data = json.loads(raw_text) # json.loads gère correctement les \u00e9 par défaut
            # -------------------------
            
            # Dans Elasticsearch, les résultats sont dans hits -> hits
            hits = data.get("hits", {}).get("hits", [])
            
            if not hits:
                print("Fin des résultats.")
                break

            for hit in hits:
                source = hit.get("_source", {})
                
                # 1. Pivot SIREN
                siren = next((item.get("id") for item in source.get("externalIds", []) if item.get("type") == "siren"), source.get("id"))

                # 2. Récupération des brevets liés
                extracted_patents = []
                for p in source.get("patents", []):
                    extracted_patents.append({
                        "external_id": str(p.get("id")), # Identifiant brevet ScanR
                        "title": p.get("title", {}).get("fr") or p.get("title", {}).get("default"),
                        "type": "patent",
                        "source_name": "scanr_link" 
                    })
                
                org_data = {
                    "external_id": siren,
                    "name": source.get("label", {}).get("default") or "Sans nom",
                    "type": "company" if source.get("is_main_parent") else "facility",
                    "city": source.get("address", [{}])[0].get("city") if source.get("address") else None,
                    "founded_date": str(source.get("creationYear")) if source.get("creationYear") else None,
                    "operating_status": source.get("status"),
                    "is_ai_related": True,
                    "patents": extracted_patents, # On passe la liste au processor
                    "raw": source 
                }
                all_results.append(org_data)
           
            print(f"Collecté {len(all_results)} organisations...", end="\r")
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Request failed: {e}")
            break

    print(f"\nTerminé. {len(all_results)} organisations récupérées.")
    return all_results