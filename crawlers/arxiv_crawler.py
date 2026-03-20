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
- MAX_RESULTS_PER_CATEGORY : Nombre total d'articles à récupérer par catégorie (repris dans le pipeline)
- FETCH_BATCH_SIZE : Nombre d'articles demandés par requête API (max 100 recommandé par arXiv).
- FETCH_DELAY : Temps de pause (secondes) entre les requêtes pour respecter les quotas de l'API.
- From_year: repris dans le pipeline (permet de limiter la profondeur des requêtes)

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
"""
Effectue l'appel technique à l'API arXiv et convertit le flux Atom/RSS en données structurées

Logique Technique :
    1. Construction de la Query : Combine la catégorie et le filtre temporel au format 
       strict d'arXiv (YYYYMMDDHHMM).
    2. Encodage : Remplace les espaces par '%20' pour respecter la norme HTTP et 
       éviter les erreurs de caractères de contrôle (InvalidURL).
    3. Tri : Force le tri par date de soumission descendante pour obtenir les 
       travaux les plus récents en priorité.
    4. Parsing : Utilise feedparser pour transformer le XML complexe d'arXiv en 
       dictionnaires Python simples, en nettoyant au passage les IDs et les titres.
"""

def get_arxiv_data(
    category: str, start_index: int = 0, max_results: int = 100, from_year: int = None
) -> List[Dict[str, Any]]:
    # Construction de la requête de base (1.)
    query = f"cat:{category}"
    
    # Si une année est spécifiée, on ajoute un intervalle de date
    # Format arXiv : [YYYYMMDDHHMM TO YYYYMMDDHHMM]
    if from_year:
        query += f" AND submittedDate:[{from_year}01010000 TO 203012312359]"

    query = query.replace(" ", "%20") #évite les crash (2.)

    url = (
        f"{BASE_ARXIV_URL}?search_query={query}"
        f"&start={start_index}&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending" # 3.
    )
    
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries: # 4.
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
"""
Cette fonction orchestre la pagination : comme l'API limite le nombre de 
résultats par requête (batch), elle boucle jusqu'à atteindre le quota demandé.

    1. Calcule la taille du prochain lot (batch) à récupérer sans dépasser le quota.
    2. Appelle get_arxiv_data pour la récupération technique et l'encodage de l'URL.
    3. Gère l'arrêt prématuré si l'API ne renvoie plus de nouveaux résultats.
    4. Incrémente l'index de départ (start_index) pour la pagination suivante.
    5. Respecte un temps de pause (FETCH_DELAY) pour éviter le bannissement par l'API.
"""
def fetch_category(category: str, max_results: int, from_year: int = None) -> List[Dict[str, Any]]:
    start_index = 0
    fetched_articles = []

    while len(fetched_articles) < max_results:
        remaining = max_results - len(fetched_articles)
        batch_size = min(FETCH_BATCH_SIZE, remaining) # 1.

        articles = get_arxiv_data(  # 2.
        category, start_index=start_index, max_results=batch_size, from_year=from_year
    )
        if not articles: # 3.
            break

        fetched_articles.extend(articles)
        start_index += batch_size # 4.
        print(f"{len(fetched_articles)} articles collected for {category} so far...")
        time.sleep(FETCH_DELAY) # 5.

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
