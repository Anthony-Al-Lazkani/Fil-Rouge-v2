
"""
Crawler pour l'extraction automatisée de publications scientifiques depuis l'API HAL.

Ce script interroge l'entrepôt national HAL pour récupérer les travaux de recherche 
français et internationaux liés à l'IA, avec un focus sur les métadonnées de structures.

Limitations Techniques :
- DOI : Présent la plupart du temps. Le filtre 'doiId_s:[* TO *]' est appliqué par défaut 
  pour garantir l'interopérabilité avec les autres sources du pipeline.
- Affiliations : HAL fournit des identifiants de structures (structId_i) et des noms 
  précis, ce qui facilite la liaison avec la table Entity.

Variables de contrôle :
- rows : Nombre de publications demandées par requête (pagination).
- pause : Temps de latence (secondes) pour respecter la courtoisie envers l'API.
- fl (Field List) : Liste des champs extraits (halId, title, date, doi, structures, auteurs, keywords).
"""

import requests
import time

class HALCrawler:
    BASE_URL = "https://api.archives-ouvertes.fr/search/"

    def __init__(self, rows=100, pause=0.2):
        self.rows = rows
        self.pause = pause

    def fetch_ai_publications(self, query: str, start_year: int, max_results: int = 100):
        """Récupère les publications HAL pour une requête donnée (passée en paramètre dans le pipeline)."""
        results = []
        start = 0
        
        while len(results) < max_results:
            params = {
                "q": query, #passée en argument dans le pipeline
                "fq": [f"producedDateY_i:[{start_year} TO *]", "doiId_s:[* TO *]"], #passé en argument dans le pipeline
                "rows": min(self.rows, max_results - len(results)), #passé en argument dans le pipeline
                "start": start,
                "wt": "json",
                "fl": "halId_s,title_s,producedDateY_i,doiId_s,docType_s,structId_i,structName_s,structType_s,structCountry_s,authFullName_s,keyword_s,domain_s"
            }
            
            response = requests.get(self.BASE_URL, params=params)
            
            #gestion des erreurs
            response.raise_for_status()
            docs = response.json().get("response", {}).get("docs", [])
            if not docs: break
            
            results.extend(docs)
            start += self.rows
            time.sleep(self.pause)
            print(f"HAL: {len(results)}/{max_results} collectés pour '{query}'...")
            
        return results