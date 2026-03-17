"""
Crawler ScanR spécialisé dans l'écosystème français de la recherche et de l'innovation IA.

Ce script interroge l'API Elasticsearch du portail ScanR (Ministère de l'Enseignement 
Supérieur et de la Recherche) pour cartographier les forces vives de l'IA en France.

Limitations Techniques :
- API Elasticsearch : Utilise des requêtes POST avec des payloads JSON complexes.
- Encodage : Nécessite un décodage manuel du texte brut pour préserver les caractères 
  spéciaux (accents) souvent corrompus par un parsing JSON standard.
- Identification : Privilégie le SIREN comme identifiant unique pour assurer 
  l'interopérabilité avec les référentiels légaux (OpenCorporates).

Variables de contrôle (Pilotables via le pipeline) :
- query : Mot-clé de recherche (ex: "intelligence artificielle").
- max_pages : Limite de profondeur de la collecte (20 résultats par page).

Fonctionnement :
Le script effectue une recherche plein texte, identifie les entreprises et laboratoires, 
et extrait simultanément les liens vers leurs brevets déposés.
"""


import requests
import time
import json
from typing import List, Dict, Any

BASE_URL = "https://scanr.enseignementsup-recherche.gouv.fr/api/scanr-organizations/_search"


def crawl_scanr_ai(query: str = "intelligence artificielle", limit: int = 100) -> List[Dict[str, Any]]:
    all_results = []
    
    size_per_page = 20
    # On calcule le nombre de pages nécessaires pour atteindre la limite
    max_pages = (limit // size_per_page) + (1 if limit % size_per_page > 0 else 0)

    # Payload standard pour Elasticsearch utilisé par ScanR
    payload = {
        "query": {
            "query_string": {
                "query": query,
                "default_operator": "AND"
            }
        },
        "size": size_per_page,
        "from": 0 # 'from' au lieu de page
    }

    print(f"=== Crawling ScanR for: {query} ===")

    for page in range(max_pages):
        payload["from"] = page * size_per_page
        
        try:
            response = requests.post(BASE_URL, json=payload)
            
            if response.status_code != 200:
                print(f"Erreur {response.status_code}: {response.text}")
                break
                

            raw_text = response.text
            data = json.loads(raw_text) #pour éviter les bugs d'encodage
            
            # Dans Elasticsearch, les résultats sont dans hits -> hits
            hits = data.get("hits", {}).get("hits", [])
            
            if not hits:
                print("Fin des résultats.")
                break

            for hit in hits:
                if len(all_results) >= limit:
                    break

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
                    "patents": extracted_patents,
                    "raw": source 
                }
                all_results.append(org_data)
           
            if len(all_results) >= limit:
                break

            print(f"Collecté {len(all_results)} organisations...", end="\r")
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Request failed: {e}")
            break

    print(f"\nTerminé. {len(all_results)} organisations récupérées.")
    return all_results