import json
import itertools
from pyalex import Works, config

# 1. IDENTIFY YOURSELF (Crucial for bulk speed: 10 req/sec vs 1 req/sec)
config.email = "anthonylazkani.22@gmail.com"
config.max_retries = 3

# 2. DEFINE FILTERS
# AI Concept ID: https://openalex.org/C41008148
AI_CONCEPT_ID = "C41008148"
START_YEAR = 2020
MAX_NUMBER_OF_ARTICLES = 100000

print(f"Initializing bulk download for Concept: {AI_CONCEPT_ID} since {START_YEAR}...")

# 3. CONFIGURE THE QUERY
# We use .filter() instead of .search() for precision
query = (
    Works()
    .filter(
        concepts={"id": AI_CONCEPT_ID},
        from_publication_date=f"{START_YEAR}-01-01"
    )
    .sort(publication_date="desc")  # Optional: get newest first
)

# 4. STREAMING TO FILE
# We use .paginate(per_page=200) which automatically handles the "cursor" for us.
# 'n_max=None' means "get everything" (no limit).

filename = "openalex_ai_bulk.jsonl"

with open(filename, "w", encoding="utf-8") as f:
    # Get the iterator (does not fetch everything at once)
    pager = query.paginate(per_page=200, n_max=MAX_NUMBER_OF_ARTICLES)

    count = 0

    # Iterate through pages (each page has up to 200 items)
    for page in pager:
        for work in page:
            # Extract only what you need to keep file size manageable
            record = {
                "id": work['id'],
                "title": work.get('title'),
                "date": work.get('publication_date'),
                "doi": work.get('doi'),
                "authors": [a['author']['display_name'] for a in work.get('authorships', [])],
                # Get the first 3 topics
                "topics": [t['display_name'] for t in work.get('topics', [])[:3]]
            }

            # Write one line per record
            f.write(json.dumps(record) + "\n")

            count += 1
            if count % 1000 == 0:
                print(f"Downloaded {count} records...", end="\r")

print(f"\nDone! Saved {count} articles to {filename}")