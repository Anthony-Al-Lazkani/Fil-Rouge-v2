from pyalex import Institutions, config
from typing import List, Dict, Any
import time

config.email = "anthonylazkani.22@gmail.com"
config.max_retries = 3

PER_PAGE = 200


def crawl_openalex_institutions() -> List[Dict[str, Any]]:
    """Crawl all institutions from OpenAlex API"""
    all_institutions = []

    print("Starting to crawl OpenAlex institutions...")

    query = Institutions().paginate(per_page=PER_PAGE)

    page_num = 0
    for page in query:
        page_num += 1
        for inst in page:
            inst_data = {
                "external_id": inst.get("id"),
                "ror": inst.get("ror"),
                "display_name": inst.get("display_name"),
                "country_code": inst.get("country_code"),
                "type": inst.get("type"),
                "homepage_url": inst.get("homepage_url"),
                "works_count": inst.get("works_count", 0),
                "cited_by_count": inst.get("cited_by_count", 0),
                "display_name_acronyms": inst.get("display_name_acronyms", []),
                "display_name_alternatives": inst.get("display_name_alternatives", []),
                "associated_institutions": [
                    {
                        "id": a.get("id"),
                        "display_name": a.get("display_name"),
                        "ror": a.get("ror"),
                        "country_code": a.get("country_code"),
                        "type": a.get("type"),
                    }
                    for a in inst.get("associated_institutions", [])
                ],
                "counts_by_year": inst.get("counts_by_year", []),
                "raw": inst,
            }
            all_institutions.append(inst_data)

        print(
            f"Page {page_num}: collected {len(all_institutions)} institutions...",
            end="\r",
        )
        time.sleep(0.05)

    print(f"\nDone. Collected {len(all_institutions)} institutions.")
    return all_institutions


if __name__ == "__main__":
    crawl_openalex_institutions()
