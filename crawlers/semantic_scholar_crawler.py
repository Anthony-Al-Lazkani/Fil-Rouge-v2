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

    def fetch_ai_papers(self, query: str, year: int, max_results: int = 100):
        all_papers = []
        offset = 0
        # S2 limite souvent à 100 par page pour les recherches textuelles
        batch_size = 100 
        
        # On garde une liste de champs stable (sans abstract si la 500 persiste)
        fields = "paperId,title,year,authors,venue,externalIds,citationCount"

        print(f"--- Crawling S2: {query} ({year}) ---")

        while len(all_papers) < max_results:
            # On ajuste le batch_size pour ne pas dépasser max_results au dernier tour
            current_limit = min(batch_size, max_results - len(all_papers))
            
            params = {
                "query": query,
                "offset": offset,
                "limit": current_limit,
                "year": str(year),
                "fields": fields
            }
            
            try:
                response = requests.get(self.BASE_URL, params=params, headers=self.headers, timeout=30)
                
                # Gestion du Rate Limit (429)
                if response.status_code == 429:
                    print("S2 Rate Limit : pause de 5 secondes...")
                    time.sleep(5)
                    continue

                # Gestion de l'erreur 500 (Problème serveur S2)
                if response.status_code == 500:
                    print("S2 Erreur 500 : tentative sans le champ abstract...")
                    # On pourrait ici retirer un champ lourd si besoin
                    break

                response.raise_for_status()
                data = response.json().get("data", [])
                
                if not data:
                    print("Plus de résultats disponibles sur S2.")
                    break

                all_papers.extend(data)
                offset += len(data)
                
                print(f"S2 : {len(all_papers)}/{max_results} récupérés (Offset: {offset})")

                # Respect du quota (important même avec une clé)
                time.sleep(0.5)

            except Exception as e:
                print(f"Erreur S2 à l'offset {offset}: {e}")
                break

        return all_papers