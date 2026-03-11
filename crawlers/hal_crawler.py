"""
Crawler HAL spécialisé dans l'IA.
Récupère les données depuis l'API et les prépare pour le processeur.
"""
import requests
import time

class HALCrawler:
    BASE_URL = "https://api.archives-ouvertes.fr/search/"

    def __init__(self, rows=100, pause=0.2):
        self.rows = rows
        self.pause = pause

    def fetch_ai_publications(self, query: str, start_year: int, max_results: int = 100):
        """Récupère les publications HAL pour une requête donnée."""
        results = []
        start = 0
        
        while len(results) < max_results:
            params = {
                "q": query,
                "fq": [f"producedDateY_i:[{start_year} TO *]", "doiId_s:[* TO *]"],
                "rows": min(self.rows, max_results - len(results)),
                "start": start,
                "wt": "json",
                "fl": "halId_s,title_s,producedDateY_i,doiId_s,docType_s,structId_i,structName_s,structType_s,structCountry_s,authFullName_s,keyword_s,domain_s"
            }
            
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            docs = response.json().get("response", {}).get("docs", [])
            
            if not docs: break
            
            results.extend(docs)
            start += self.rows
            time.sleep(self.pause)
            print(f"HAL: {len(results)}/{max_results} collectés pour '{query}'...")
            
        return results