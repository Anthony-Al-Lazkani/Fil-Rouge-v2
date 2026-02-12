from pyalex import Works, config
from database import get_session
from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from services.author_service import AuthorService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate
from schemas.author import AuthorCreate

import time

# ------------------ CONFIG ------------------
config.email = "anthonylazkani.22@gmail.com"
config.max_retries = 3

AI_CONCEPT_ID = "C41008148"
START_YEAR = 2026
END_YEAR = 2026
PER_PAGE = 100

# ------------------ SERVICES ------------------
source_service = SourceService()
item_service = ResearchItemService()
author_service = AuthorService()
session = next(get_session())

# Create or get OpenAlex source
openalex = source_service.create(
    session,
    SourceCreate(
        name="openalex",
        type="academic",
        base_url="https://openalex.org/",
    ),
)


# ------------------ HELPER ------------------
def exists(external_id: str) -> bool:
    return (
        item_service.get_by_external_id(session, openalex.id, external_id) is not None
    )


# ------------------ MAIN LOOP ------------------
count = 0

for year in range(START_YEAR, END_YEAR + 1):
    print(f"\n=== Crawling year {year} ===")

    query = (
        Works()
        .filter(concepts={"id": AI_CONCEPT_ID}, publication_year=year)
        .sort(publication_date="desc")
    )

    pager = query.paginate(per_page=PER_PAGE)

    for page in pager:
        for work in page:
            external_id = work.get("id")
            title = work.get("title")
            doi = work.get("doi")

            # Skip if already in DB
            if exists(external_id):
                continue

            # Skip deprecated works
            if title is None or title.lower() == "deprecated":
                continue

            loc = work.get("primary_location") or {}

            # Extract authors with full details and create them in database
            author_ids = []
            authors = []
            for idx, auth in enumerate(work.get("authorships", [])):
                a = auth.get("author", {})
                author_affiliations = []
                for aff in auth.get("affiliations", []):
                    author_affiliations.append(
                        {
                            "id": aff.get("id"),
                            "display_name": aff.get("display_name"),
                            "ror": aff.get("ror"),
                            "country_code": aff.get("country_code"),
                            "type": aff.get("type"),
                        }
                    )

                roles = []
                if auth.get("is_corresponding"):
                    roles.append("corresponding_author")
                if idx == 0:
                    roles.append("first_author")
                if not roles:
                    roles.append("co_author")

                author_data = {
                    "author_id": a.get("id"),
                    "display_name": a.get("display_name"),
                    "orcid": a.get("orcid"),
                    "raw_author_name": auth.get("raw_author_name"),
                    "roles": roles,
                    "affiliations": author_affiliations,
                    "countries": auth.get("countries", []),
                }
                authors.append(author_data)

                # Create author in database
                author_create = AuthorCreate(
                    full_name=a.get("display_name") or auth.get("raw_author_name", ""),
                    external_id=str(a.get("id")) if a.get("id") else None,
                    orcid=a.get("orcid"),
                    roles=roles,
                    affiliations=author_affiliations,
                )
                author = author_service.create(session, author_create)
                author_ids.append(author.id)

            # Extract location info
            loc = work.get("primary_location") or {}
            source_info = loc.get("source") or {}

            # Build ResearchItem
            research_item = ResearchItemCreate(
                source_id=openalex.id,
                external_id=external_id,
                type=work.get("type", "article"),
                doi=work.get("doi"),
                title=title,
                abstract=work.get("abstract"),
                year=work.get("publication_year"),
                publication_date=work.get("publication_date"),
                language=work.get("language"),
                is_retracted=work.get("is_retracted", False),
                is_open_access=loc.get("is_oa", False),
                license=loc.get("license"),
                url=loc.get("landing_page_url"),
                citation_count=work.get("cited_by_count", 0),
                keywords=[kw.get("display_name") for kw in work.get("keywords", [])]
                if work.get("keywords")
                else [],
                topics=[t.get("display_name") for t in work.get("topics", [])]
                if work.get("topics")
                else [],
                metrics={
                    "author_ids": author_ids,
                    "authors": authors,
                    "open_access_location": loc.get("landing_page_url"),
                    "source_name": source_info.get("display_name"),
                    "source_issn": source_info.get("issn"),
                    "source_type": source_info.get("type"),
                    "version": loc.get("version"),
                    "is_accepted": loc.get("is_accepted"),
                    "is_published": loc.get("is_published"),
                    "referenced_works": work.get("referenced_works", [])[
                        :10
                    ],  # Limit to first 10
                    "related_works": work.get("related_works", [])[:5],
                },
                raw=work,
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
    print(
        f"{item.id} | {item.external_id} | {item.title} | {item.year} | OA: {item.is_open_access}"
    )
