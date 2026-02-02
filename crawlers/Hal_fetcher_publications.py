"""
Responsabilité unique : interroger HAL proprement.
S'utilise en complément de Hal_Bulk_Publications.py
Le point d'entrée est Hal_Bulk_Publications.py
Lien pour voir les champs: https://api.archives-ouvertes.fr/docs/search/?schema=fields#fields
"""

import requests
import time

class HALPublicationFetcher:
    BASE_URL = "https://api.archives-ouvertes.fr/search/"

    def __init__(self, rows=200, pause=0.2):
        self.rows = rows
        self.pause = pause

    def fetch(self, query, start_year, start=0):
        params = {
            "q": query,
            "fq": [
                f"producedDateY_i:[{start_year} TO *]",
                "doiId_s:[\"\" TO *]"
            ],
            "rows": self.rows,
            "start": start,
            "wt": "json",
            "fl": (
                "halId_s,title_s,producedDateY_i,doiId_s,docType_s,"
                "structId_i,structName_s,structType_s,structCountry_s,"
                "authFullName_s,keyword_s,domain_s"
            )
        }


        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()
        time.sleep(self.pause)
        
        data = response.json()
        return data.get("response", {}).get("docs", [])