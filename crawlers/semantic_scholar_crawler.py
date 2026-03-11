"""
Crawler Semantic Scholar spécialisé dans l'IA.
Gère les requêtes paginées et le respect des limites de l'API.
"""
import requests
import time

class SemanticScholarCrawler:
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self, api_key: str = None, limit: int = 100):
        self.headers = {"x-api-key": api_key} if api_key else {}
        self.limit = limit

    def fetch_ai_papers(self, query: str, year: int, max_results: int = 10):
        """Récupère les articles pour une requête et une année précise."""
        # On enlève 'language' qui fait planter l'API
        fields = "paperId,title,abstract,year,authors,citationCount,venue,fieldsOfStudy,externalIds,url,openAccessPdf"
        
        params = {
            "query": query,
            "offset": 0,
            "limit": max_results,
            "year": str(year),
            "fields": fields
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                print(f"Erreur API S2 {response.status_code}: {response.text}")
                return []

            return response.json().get("data", [])
            
        except Exception as e:
            print(f"Erreur système S2: {e}")
            return []