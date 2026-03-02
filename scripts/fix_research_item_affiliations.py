"""
Script to fix research_item metrics by extracting proper affiliations from raw data
"""

import json
from database import get_session
from models.research_item import ResearchItem
from sqlmodel import select


def fix_research_item_affiliations():
    session = next(get_session())

    items = session.exec(select(ResearchItem)).all()
    fixed_count = 0

    for item in items:
        raw = item.raw
        if isinstance(raw, str):
            raw = json.loads(raw)

        authorships = raw.get("authorships", [])
        if not authorships:
            continue

        # Rebuild authors with proper affiliations from raw data
        new_authors = []
        for idx, auth in enumerate(authorships):
            a = auth.get("author", {})
            author_affiliations = []

            # Use institutions instead of affiliations (fix for OpenAlex)
            for inst in auth.get("institutions", []):
                author_affiliations.append(
                    {
                        "id": inst.get("id"),
                        "display_name": inst.get("display_name"),
                        "ror": inst.get("ror"),
                        "country_code": inst.get("country_code"),
                        "type": inst.get("type"),
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
            new_authors.append(author_data)

        # Update metrics
        metrics = item.metrics
        if isinstance(metrics, str):
            metrics = json.loads(metrics)

        metrics["authors"] = new_authors

        item.metrics = metrics
        session.add(item)
        fixed_count += 1

        if fixed_count % 100 == 0:
            session.commit()
            print(f"Fixed {fixed_count} items...")

    session.commit()
    print(f"Done. Fixed {fixed_count} research items.")


if __name__ == "__main__":
    fix_research_item_affiliations()
