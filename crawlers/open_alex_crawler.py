# from pyalex import Works, config
# from database import get_session
# from services.research_item_service import ResearchItemService
# from services.source_service import SourceService
# from schemas.research_item import ResearchItemCreate
# from schemas.source import SourceCreate
#
# # 1. SETUP
# config.email = "anthonylazkani.22@gmail.com"
# config.max_retries = 3
#
# AI_CONCEPT_ID = "C41008148"
# TARGET_COUNT = 10000
#
# # 2. Services
# source_service = SourceService()
# item_service = ResearchItemService()
#
# # Session
# session = next(get_session())
#
# # create or get OpenAlex source
# openalex = source_service.create(session, SourceCreate(
#     name="openalex",
#     type="academic",
#     base_url="https://openalex.com/",
#     )
# )
#
# # 3. QUERY
# query = (
#     Works()
#     .filter(
#         concepts={"id": AI_CONCEPT_ID},
#         from_publication_date="2020-01-01"
#     )
#     .sort(publication_date="desc")
# )
#
# pager = query.paginate(per_page=200, n_max=TARGET_COUNT)
#
# count = 0
# for page in pager:
#     for work in page:
#
#         # --- A. LOCATION / ACCESS INFO ---
#         loc = work.get('primary_location') or {}
#         source_info = loc.get('source') or {}
#
#         # --- B. AUTHORS (simplified for DB)
#         authors = []
#         for auth in work.get('authorships', []):
#             author_details = auth.get('author', {})
#             authors.append({
#                 "author_id": author_details.get('id'),
#                 "display_name": author_details.get('display_name'),
#                 "orcid": author_details.get('orcid'),
#                 "raw_author_name": auth.get('raw_author_name'),
#                 "is_corresponding": auth.get('is_corresponding')
#             })
#
#         # --- C. BUILD SERVICE SCHEMA ---
#         research_item = ResearchItemCreate(
#             source_id=openalex.id,
#             external_id=work.get('id'),
#             type="article",
#             title=work.get('title'),
#             year=work.get('publication_year'),
#             is_retracted=work.get('is_retracted', False),
#             is_open_access=loc.get('is_oa', False),
#             metrics={"topics": [t['display_name'] for t in work.get('topics', [])], "authors": authors},
#             raw=work  # store full raw record
#         )
#
#         # --- D. INSERT INTO DB ---
#         item_service.create(session, research_item)
#
#         count += 1
#         if count % 100 == 0:
#             print(f"Inserted {count} articles...", end="\r")
#
# print(f"\nCompleted. {count} articles saved to the database!")
#
# # Fetch all articles and print a few columns
# all_items = item_service.get_all(session)
# print(f"\nTotal items in DB: {len(all_items)}")
# for item in all_items[:10]:  # print first 10 for readability
#     print(f"{item.id} | {item.external_id} | {item.title} | {item.year} | OA: {item.is_open_access}")
#

from pyalex import Works, config
from database import get_session
from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate

import time

# ------------------ CONFIG ------------------
config.email = "anthonylazkani.22@gmail.com"
config.max_retries = 3

AI_CONCEPT_ID = "C41008148"
START_YEAR = 2020
END_YEAR = 2026
PER_PAGE = 200

# ------------------ SERVICES ------------------
source_service = SourceService()
item_service = ResearchItemService()
session = next(get_session())

# Create or get OpenAlex source
openalex = source_service.create(session, SourceCreate(
    name="openalex",
    type="academic",
    base_url="https://openalex.org/",
))

# ------------------ HELPER ------------------
def exists(external_id: str) -> bool:
    return item_service.get_by_external_id(session, openalex.id, external_id) is not None

# ------------------ MAIN LOOP ------------------
count = 0

for year in range(START_YEAR, END_YEAR + 1):
    print(f"\n=== Crawling year {year} ===")

    query = (
        Works()
        .filter(
            concepts={"id": AI_CONCEPT_ID},
            publication_year=year
        )
        .sort(publication_date="desc")
    )

    pager = query.paginate(per_page=PER_PAGE)

    for page in pager:
        for work in page:
            external_id = work.get("id")
            title = work.get("title")

            # Skip if already in DB
            if exists(external_id):
                continue

            # Skip deprecated works
            if title is None or title.lower() == "deprecated":
                continue

            loc = work.get('primary_location') or {}

            # Extract authors
            authors = []
            for auth in work.get('authorships', []):
                a = auth.get('author', {})
                authors.append({
                    "author_id": a.get('id'),
                    "display_name": a.get('display_name'),
                    "orcid": a.get('orcid'),
                    "raw_author_name": auth.get('raw_author_name'),
                    "is_corresponding": auth.get('is_corresponding')
                })

            # Build ResearchItem
            research_item = ResearchItemCreate(
                source_id=openalex.id,
                external_id=external_id,
                type="article",
                title=title,
                year=work.get('publication_year'),
                is_retracted=work.get('is_retracted', False),
                is_open_access=loc.get('is_oa', False),
                metrics={
                    "topics": [t['display_name'] for t in work.get('topics', [])],
                    "authors": authors,
                    "open_access_location": loc.get('url'),
                },
                raw=work
            )

            # Insert into DB
            item_service.create(session, research_item)
            count += 1

            if count % 100 == 0:
                print(f"Inserted {count} articles...", end="\r")

            # Optional: small pause to be polite
            time.sleep(0.01)

print(f"\nDone. Inserted {count} clean articles.")

# ------------------ REPORT ------------------
all_items = item_service.get_all(session)
print(f"\nTotal items in DB: {len(all_items)}")
for item in all_items[:10]:  # first 10
    print(f"{item.id} | {item.external_id} | {item.title} | {item.year} | OA: {item.is_open_access}")
