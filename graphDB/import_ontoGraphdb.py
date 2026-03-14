"""
installer graphDb soit via docker, soit via l'appli de bureau
lancer graphDB sur le port 7200
lancer import_ontoGraphdb.py
charge l'ontologie version ttl
"""
import requests

GRAPHDB_URL = "http://localhost:7200"
REPO_ID = "fil-rougev1"

def load_file(filepath):
    with open(filepath, "rb") as f:
        response = requests.post(
            f"{GRAPHDB_URL}/repositories/{REPO_ID}/statements",
            headers={"Content-Type": "text/turtle"},
            data=f.read()
        )

    if response.status_code == 204:
        print(f"✅ {filepath} chargé avec succès")
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")


def count_triples():
    response = requests.get(
        f"{GRAPHDB_URL}/repositories/{REPO_ID}",
        params={"query": "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }"},
        headers={"Accept": "application/sparql-results+json"}
    )
    count = response.json()["results"]["bindings"][0]["count"]["value"]
    print(f"Nombre de triples : {count}")

if __name__ == "__main__":
    load_file("../ontologie/onto_v3.ttl")
    count_triples()