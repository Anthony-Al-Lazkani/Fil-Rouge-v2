import time
import feedparser

from database import get_session
from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate

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
FETCH_BATCH_SIZE = 100           # how many results to fetch per request
FETCH_DELAY = 0.5                # seconds between requests
POST_DELAY = 0.05                # optional small delay per article

# ------------------ SERVICES ------------------
session = next(get_session())
source_service = SourceService()
item_service = ResearchItemService()

# Create/get source for ArXiv
arxiv_source = source_service.create(session, SourceCreate(
    name="arxiv",
    type="academic",
    base_url="https://arxiv.org/"
))

# ------------------ HELPER ------------------
def exists(source_id: int, external_id: str) -> bool:
    """Check if an article already exists in the DB"""
    return item_service.get_by_external_id(session, source_id, external_id) is not None

def get_arxiv_data(category: str, start_index: int = 0, max_results: int = 100):
    url = (
        f"{BASE_ARXIV_URL}?search_query=cat:{category}"
        f"&start={start_index}&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        articles.append({
            "id": entry.id.split('/')[-1],
            "title": entry.title.strip(),
            "summary": entry.summary.strip(),
            "published": entry.published,
            "authors": [author.name for author in entry.authors],
            "category": category
        })
    return articles

# ------------------ FETCHING ------------------
def fetch_category(category: str):
    start_index = 0
    fetched_count = 0

    while fetched_count < MAX_RESULTS_PER_CATEGORY:
        remaining = MAX_RESULTS_PER_CATEGORY - fetched_count
        batch_size = min(FETCH_BATCH_SIZE, remaining)

        articles = get_arxiv_data(category, start_index=start_index, max_results=batch_size)
        if not articles:
            break

        for article in articles:
            ext_id = article["id"]

            if exists(arxiv_source.id, ext_id):
                continue  # skip duplicates

            research_item = ResearchItemCreate(
                source_id=arxiv_source.id,
                external_id=ext_id,
                type="article",
                title=article["title"],
                year=int(article["published"][:4]),
                is_retracted=False,
                is_open_access=True,
                metrics={
                    "authors": article["authors"],
                    "summary": article["summary"],
                    "category": article["category"],
                    "published": article["published"]
                },
                raw=article
            )

            item_service.create(session, research_item)
            fetched_count += 1
            time.sleep(POST_DELAY)

        start_index += batch_size
        print(f"{fetched_count} articles collected for {category} so far...")
        time.sleep(FETCH_DELAY)

    print(f"Finished category {category}: {fetched_count} articles collected.\n")
    return fetched_count

# ------------------ MAIN ------------------
def crawl_ai_articles():
    total_articles = 0
    for category in AI_CATEGORIES:
        print(f"=== Crawling category {category} ===")
        count = fetch_category(category)
        total_articles += count

    print(f"\nTotal AI articles collected: {total_articles}")

if __name__ == "__main__":
    crawl_ai_articles()
