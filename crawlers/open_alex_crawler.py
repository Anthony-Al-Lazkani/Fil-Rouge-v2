from pyalex import Works, config
from database import get_session
from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate

# 1. SETUP
config.email = "anthonylazkani.22@gmail.com"
config.max_retries = 3

AI_CONCEPT_ID = "C41008148"
TARGET_COUNT = 2000

# 2. Services
source_service = SourceService()
item_service = ResearchItemService()

# Session
session = next(get_session())

# create or get OpenAlex source
openalex = source_service.create(session, SourceCreate(
    name="openalex",
    type="academic",
    base_url="https://openalex.com/",
    )
)

# 3. QUERY
query = (
    Works()
    .filter(
        concepts={"id": AI_CONCEPT_ID},
        from_publication_date="2020-01-01"
    )
    .sort(publication_date="desc")
)

pager = query.paginate(per_page=200, n_max=TARGET_COUNT)

count = 0
for page in pager:
    for work in page:

        # --- A. LOCATION / ACCESS INFO ---
        loc = work.get('primary_location') or {}
        source_info = loc.get('source') or {}

        # --- B. AUTHORS (simplified for DB)
        authors = []
        for auth in work.get('authorships', []):
            author_details = auth.get('author', {})
            authors.append({
                "author_id": author_details.get('id'),
                "display_name": author_details.get('display_name'),
                "orcid": author_details.get('orcid'),
                "raw_author_name": auth.get('raw_author_name'),
                "is_corresponding": auth.get('is_corresponding')
            })

        # --- C. BUILD SERVICE SCHEMA ---
        research_item = ResearchItemCreate(
            source_id=openalex.id,
            external_id=work.get('id'),
            type="article",
            title=work.get('title'),
            year=work.get('publication_year'),
            is_retracted=work.get('is_retracted', False),
            is_open_access=loc.get('is_oa', False),
            references=work.get('references_works', []),
            metrics={"topics": [t['display_name'] for t in work.get('topics', [])], "authors": authors},
            raw=work  # store full raw record
        )

        # --- D. INSERT INTO DB ---
        item_service.create(session, research_item)

        count += 1
        if count % 100 == 0:
            print(f"Inserted {count} articles...", end="\r")

print(f"\nCompleted. {count} articles saved to the database!")

# Fetch all articles and print a few columns
all_items = item_service.get_all(session)
print(f"\nTotal items in DB: {len(all_items)}")
for item in all_items[:10]:  # print first 10 for readability
    print(f"{item.id} | {item.external_id} | {item.title} | {item.year} | OA: {item.is_open_access}")

