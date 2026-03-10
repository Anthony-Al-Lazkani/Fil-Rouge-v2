import requests

GRAPHDB_URL = "http://localhost:7200"
REPO_ID = "fil-rougev2"


def create_repository():
    # Envoyer le fichier TTL en multipart/form-data
    with open("repo-config.ttl", "rb") as f:
        response = requests.post(
            f"{GRAPHDB_URL}/rest/repositories",
            files={"config": ("repo-config.ttl", f, "multipart/form-data")}
        )

    if response.status_code in [200, 201]:
        print(f"✅ Repository '{REPO_ID}' créé")
    elif response.status_code == 409:
        print(f"⚠️ Repository '{REPO_ID}' existe déjà")
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")


def test_connection():
    response = requests.get(
        f"{GRAPHDB_URL}/repositories/{REPO_ID}",
        params={"query": "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }"},
        headers={"Accept": "application/sparql-results+json"}
    )

    if response.status_code == 200:
        count = response.json()["results"]["bindings"][0]["count"]["value"]
        print(f"✅ Connexion OK - {count} triples")
    else:
        print(f"❌ Erreur de connexion")


if __name__ == "__main__":
    create_repository()
    test_connection()
