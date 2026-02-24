import time
import feedparser
from typing import List, Dict, Any

# ------------------ CONFIG ------------------
AI_CATEGORIES = [
    "cs.AI",  # Artificial Intelligence
    "cs.LG",  # Machine Learning
    "cs.NE",  # Neural and Evolutionary Computing
    "cs.CV",  # Computer Vision (optional)
]

BASE_ARXIV_URL = "https://export.arxiv.org/api/query"

# Limits
MAX_RESULTS_PER_CATEGORY = 10  # you can change this whenever
FETCH_BATCH_SIZE = 100  # how many results to fetch per request
FETCH_DELAY = 0.5  # seconds between requests
POST_DELAY = 0.05  # optional small delay per article


# ------------------ HELPER ------------------
def get_arxiv_data(
    category: str, start_index: int = 0, max_results: int = 100
) -> List[Dict[str, Any]]:
    url = (
        f"{BASE_ARXIV_URL}?search_query=cat:{category}"
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
def fetch_category(category: str) -> List[Dict[str, Any]]:
    start_index = 0
    fetched_articles = []

    while len(fetched_articles) < MAX_RESULTS_PER_CATEGORY:
        remaining = MAX_RESULTS_PER_CATEGORY - len(fetched_articles)
        batch_size = min(FETCH_BATCH_SIZE, remaining)

        articles = get_arxiv_data(
            category, start_index=start_index, max_results=batch_size
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
def crawl_ai_articles() -> List[Dict[str, Any]]:
    all_articles = []
    for category in AI_CATEGORIES:
        print(f"=== Crawling category {category} ===")
        articles = fetch_category(category)
        all_articles.extend(articles)

    print(f"\nTotal AI articles collected: {len(all_articles)}")
    return all_articles


if __name__ == "__main__":
    crawl_ai_articles()
