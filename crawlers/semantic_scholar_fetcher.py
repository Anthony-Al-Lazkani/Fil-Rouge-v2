import requests
import time

class SemanticScholarFetcher:
    def __init__(self, api_key=None, limit=100):
        self.api_key = api_key
        self.limit = limit
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        self.headers = {}
        if api_key:
            self.headers["x-api-key"] = api_key

    def fetch(self, query, year_min=None, year_max=None, offset=0):
        """
        Recherche des articles sur Semantic Scholar

        Args:
            query (str): Requête de recherche
            year_min (int, optional): Année minimale (incluse)
            year_max (int, optional): Année maximale (incluse)
            offset (int): Position de départ dans les résultats

        Returns:
            list: Liste des articles trouvés
        """
        params = {
            "query": query,
            "offset": offset,
            "limit": self.limit,
            "fields": "paperId,title,abstract,year,authors,citationCount,venue,fieldsOfStudy,externalIds,url,references"
        }

        # Gestion du filtre année
        if year_min and year_max:
            params["year"] = f"{year_min}-{year_max}"  # Range : 2022-2024
        elif year_min:
            params["year"] = f"{year_min}-"  # À partir de : 2022-
        elif year_max:
            params["year"] = f"-{year_max}"  # Jusqu'à : -2024

        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            return data.get("data", [])

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print("  Rate limit atteint, pause de 60 secondes...")
                time.sleep(60)
                return self.fetch(query, year_min, year_max, offset)
            else:
                print(f" Erreur HTTP {e.response.status_code}: {e}")
                return []

        except requests.exceptions.RequestException as e:
            print(f" Erreur de requête: {e}")
            return []
