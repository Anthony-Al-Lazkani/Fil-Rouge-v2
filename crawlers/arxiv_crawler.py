"""
Crawler pour l'extraction automatisée de publications depuis l'API arXiv.

Ce script interroge les archives d'arXiv pour récupérer les derniers travaux en IA 
(Computer Science / Machine Learning / Artificial Intelligence).

Limitations Techniques :
- DOI : Généralement NULL. arXiv étant un dépôt de preprints, le DOI n'est attribué 
  qu'après publication en revue (souvent non répertorié dans le flux API initial).
- Affiliations/ORCID : Non fournis par l'API standard d'arXiv.

Variables de contrôle :
- AI_CATEGORIES : Liste des domaines arXiv à scanner (cs.AI, cs.LG, etc.).
- MAX_RESULTS_PER_CATEGORY : Nombre total d'articles à récupérer par catégorie. 
- FETCH_BATCH_SIZE : Nombre d'articles demandés par requête API (max 100 recommandé par arXiv).
- FETCH_DELAY : Temps de pause (secondes) entre les requêtes pour respecter les quotas de l'API.

Fonctionnement :
Le script itère sur les catégories, effectue des requêtes paginées jusqu'à atteindre 
le quota fixé, et renvoie une liste de dictionnaires formatés pour l'ArxivProcessor.
"""

import time
import feedparser
from typing import List, Dict, Any

# ------------------ CONFIG ------------------
AI_CATEGORIES = [
    "cs.AI",  # Artificial Intelligence
    "cs.LG",  # Machine Learning
    "cs.MA",  # Covers multiagent systems, distributed artificial intelligence, intelligent agents, coordinated interactions. and practical applications
    "cs.NE",  # Neural and Evolutionary Computing
]

BASE_ARXIV_URL = "https://export.arxiv.org/api/query"

# Limits
MAX_RESULTS_PER_CATEGORY = 3000  # you can change this whenever
FETCH_BATCH_SIZE = 100  # how many results to fetch per request
FETCH_DELAY = 0.5  # seconds between requests
POST_DELAY = 0.05  # optional small delay per article


# ------------------ HELPER ------------------
def get_arxiv_data(
    category: str, start_index: int = 0, max_results: int = 100, from_year: int = None
) -> List[Dict[str, Any]]:
    # Construction de la requête de base
    query = f"cat:{category}"
    
    # Si une année est spécifiée, on ajoute un intervalle de date
    # Format arXiv : [YYYYMMDDHHMM TO YYYYMMDDHHMM]
    if from_year:
        query += f" AND submittedDate:[{from_year}01010000 TO 203012312359]"

    url = (
        f"{BASE_ARXIV_URL}?search_query={query}"
        f"&start={start_index}&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )
    
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        articles.append(
            {
                "id": entry.id.split("/")[-1],
                "title": entry.title.strip(),
                "summary": entry.summary.strip(),
                "published": entry.published,
                "authors": [author.name for author in entry.authors],
                "category": category,
            }
        )
    return articles


# ------------------ FETCHING ------------------
def fetch_category(category: str, max_results: int, from_year: int = None) -> List[Dict[str, Any]]:
    start_index = 0
    fetched_articles = []

    # On utilise max_results passé en paramètre ici
    while len(fetched_articles) < max_results:
        remaining = max_results - len(fetched_articles)
        batch_size = min(FETCH_BATCH_SIZE, remaining)

        articles = get_arxiv_data(
        category, start_index=start_index, max_results=batch_size, from_year=from_year
    )
        if not articles:
            break

        fetched_articles.extend(articles)
        start_index += batch_size
        print(f"{len(fetched_articles)} articles collected for {category} so far...")
        time.sleep(FETCH_DELAY)

    print(
        f"Finished category {category}: {len(fetched_articles)} articles collected.\n"
    )
    return fetched_articles


# ------------------ MAIN ------------------
def crawl_ai_articles(max_results_per_cat: int = MAX_RESULTS_PER_CATEGORY, from_year: int = None) -> List[Dict[str, Any]]:
    all_articles = []
    for category in AI_CATEGORIES:
        print(f"=== Crawling category {category} ===")
        
        articles = fetch_category(category, max_results=max_results_per_cat, from_year=from_year)
        all_articles.extend(articles)

    print(f"\nTotal AI articles collected: {len(all_articles)}")
    return all_articles


if __name__ == "__main__":
    crawl_ai_articles()
