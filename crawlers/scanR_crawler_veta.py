import requests
import json

BASE_URL = "https://scanr.enseignementsup-recherche.gouv.fr/api/scanr-organizations/_search"

def inspect_one_org():
    payload = {
        "query": {"query_string": {"query": "intelligence artificielle"}},
        "size": 1
    }
    
    response = requests.post(BASE_URL, json=payload)
    if response.status_code == 200:
        data = response.json()
        hits = data.get("hits", {}).get("hits", [])
        
        if hits:
            # On récupère l'objet source complet
            full_obj = hits[0].get("_source", {})
            
            print("=== LISTE DES CLÉS DISPONIBLES DANS SCANR ===")
            print(list(full_obj.keys()))
            print("\n=== APERÇU DU CONTENU (JSON) ===")
            print(json.dumps(full_obj, indent=2, ensure_ascii=False))
        else:
            print("Aucun résultat.")
    else:
        print(f"Erreur: {response.status_code}")

if __name__ == "__main__":
    inspect_one_org()