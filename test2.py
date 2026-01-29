import json
from pyalex import Works, config

# 1. SETUP
config.email = "anthonylazkani.22@gmail.com"
config.max_retries = 3

AI_CONCEPT_ID = "C41008148"
TARGET_COUNT = 10000

print(f"Extracting deep metadata for {TARGET_COUNT} works...")

# 2. QUERY
query = (
    Works()
    .filter(
        concepts={"id": AI_CONCEPT_ID},
        from_publication_date="2020-01-01"
    )
    .sort(publication_date="desc")
)

filename = "dataset.jsonl"


# --- HELPER: Safe Extraction ---
def safe_get(data, key, default=None):
    """Returns None (null) instead of crashing if key missing"""
    return data.get(key, default)


with open(filename, "w", encoding="utf-8") as f:
    pager = query.paginate(per_page=200, n_max=TARGET_COUNT)

    count = 0
    for page in pager:
        for work in page:

            # --- A. LOCATION / ACCESS INFO ---
            # primary_location can be None, so we check first
            loc = work.get('primary_location') or {}
            source = loc.get('source') or {}

            # --- B. AUTHORSHIPS & INSTITUTIONS (The Ontology Core) ---
            processed_authors = []

            for auth in work.get('authorships', []):
                author_details = auth.get('author', {})

                # Extract Institutions for this specific author
                processed_insts = []
                for inst in auth.get('institutions', []):
                    processed_insts.append({
                        "id": inst.get('id'),
                        "display_name": inst.get('display_name'),
                        "ror": inst.get('ror'),
                        "country_code": inst.get('country_code'),
                        "type": inst.get('type'),
                        "lineage": inst.get('lineage', [])  # Helpful for linking parent orgs
                    })

                # Build Author Object
                processed_authors.append({
                    "author_id": author_details.get('id'),
                    "display_name": author_details.get('display_name'),
                    "orcid": author_details.get('orcid'),
                    "raw_author_name": auth.get('raw_author_name'),  # Name as it appeared in the paper
                    "is_corresponding": auth.get('is_corresponding'),
                    "countries": auth.get('countries'),
                    "raw_affiliation_strings": auth.get('raw_affiliation_strings'),
                    "affiliations": processed_insts  # NESTED LIST
                })

            # --- C. BUILD THE MASTER RECORD ---
            record = {
                # Work Identifiers
                "id": work.get('id'),
                "doi": work.get('doi'),
                "title": work.get('title'),
                "display_name": work.get('display_name'),

                # Dates
                "publication_year": work.get('publication_year'),
                "publication_date": work.get('publication_date'),

                # Metadata
                "language": work.get('language'),
                "type": work.get('type'),
                "is_retracted": work.get('is_retracted'),  # Crucial for data quality

                # Access / Location
                "primary_location": {
                    "is_oa": loc.get('is_oa'),
                    "landing_page_url": loc.get('landing_page_url'),
                    "license": loc.get('license'),
                    "version": loc.get('version'),
                    "is_accepted": loc.get('is_accepted'),
                    "is_published": loc.get('is_published'),
                    "source_name": source.get('display_name'),
                    "source_issn": source.get('issn_l'),
                    "source_type": source.get('type')
                },

                # The Relations
                "authorships": processed_authors,

                # Topics (Categories) for classification
                "topics": [t['display_name'] for t in work.get('topics', [])]
            }

            # Dump to JSONL (Python None becomes JSON null)
            f.write(json.dumps(record) + "\n")

            count += 1
            if count % 1000 == 0:
                print(f"Processed {count} records...", end="\r")

print(f"\nCompleted. Data saved to {filename}")