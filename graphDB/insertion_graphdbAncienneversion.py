"""
fonction d'insertion d'instance dans graphDB
N'insère que si n'existe pas déjà
"""

import requests

GRAPHDB_URL = "http://localhost:7200"
REPO_ID = "fil-rouge"

def insert_sparql_raw(query):
    response = requests.post(
        f"{GRAPHDB_URL}/repositories/{REPO_ID}/statements",
        headers={"Content-Type": "application/sparql-update"},
        data=query
    )
    if response.status_code == 204:
        return True
    else:
        print(f"❌ {response.status_code} - {response.text}")
        return False

if __name__ == "__main__":
    test = """
        PREFIX : <http://example.org/veille#>
        INSERT { :Test_Chercheur a :Chercheur ; :nom "Test Chercheur" . }
        WHERE { FILTER NOT EXISTS { :Test_Chercheur a :Chercheur } }
    """
    print("1er appel :", insert_sparql_raw(test))
    print("2e appel :", insert_sparql_raw(test))
