"""
Logique métier + écriture fichier
Il n'y a pas de données country renseignées sur HAL - l'exemple exposé ci-dessous doit être une exception
voir: https://api.archives-ouvertes.fr/search/?q=intelligence%20artificielle&rows=1&fl=*&wt=json pour obtenir les noms des champs
"""

import json
from Hal_fetcher_publications import HALPublicationFetcher
from pathlib import Path


QUERY = '"intelligence artificielle"'
START_YEAR = 2019
MAX_RECORDS = 10_000

Path("data").mkdir(parents=True, exist_ok=True)

fetcher = HALPublicationFetcher()
start = 0
count = 0


with open("data/hal_publications.jsonl", "w", encoding="utf-8") as f:
    while count < MAX_RECORDS:
        docs = fetcher.fetch(QUERY, START_YEAR, start=start)
        if not docs:
            break

        for doc in docs:
            record = {
                "publication": {
                    "id": doc.get("halId_s"),
                    "title": doc.get("title_s"),
                    "year": doc.get("producedDateY_i"),
                    "doi": doc.get("doiId_s"),
                    "domains": doc.get("domain_s", []),
                    "keywords": doc.get("keyword_s", []),
                },

                "authors": doc.get("authFullName_s", [])
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

            if count >= MAX_RECORDS:
                break

        start += fetcher.rows
        print(f"{count} notices collectées…", end="\r")

print("\nTéléchargement terminé.")
