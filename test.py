import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "database.db"


def normalize_name(name: str) -> str | None:
    """Normalize name for exact matching."""
    if not name or name.strip() in ("", "N/A", "nan", "None"):
        return None
    name = name.lower().strip()
    name = " ".join(name.split())
    return name.strip()


def get_all_founders():
    """Get all unique founders from database."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, founders FROM organization WHERE founders IS NOT NULL"
    )
    rows = cur.fetchall()
    conn.close()

    founders = {}
    for org_id, org_name, founders_json in rows:
        if founders_json:
            try:
                founder_list = json.loads(founders_json)
                for f in founder_list:
                    normalized = normalize_name(f)
                    if normalized:
                        founders[normalized] = {"founder": f, "organization": org_name}
            except:
                pass
    return founders


def check_authors_in_startups():
    """Check if any authors from database match startup founders."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, full_name FROM author")
    authors = cur.fetchall()
    conn.close()

    founders = get_all_founders()

    print(f"Loaded {len(founders)} unique founders from database")
    print(f"Checking {len(authors)} authors from database...\n")

    matches = []

    for author_id, full_name in authors:
        normalized_author = normalize_name(full_name)
        if not normalized_author:
            continue

        if normalized_author in founders:
            matches.append(
                {
                    "author_id": author_id,
                    "author_name": full_name,
                    "founder_name": founders[normalized_author]["founder"],
                    "organization": founders[normalized_author]["organization"],
                }
            )

    if matches:
        print("MATCHES FOUND:")
        print("-" * 80)
        for m in matches:
            print(f"Author: {m['author_name']}")
            print(f"Founder: {m['founder_name']}")
            print(f"Startup: {m['organization']}")
            print("-" * 80)
    else:
        print("False")

    return matches


if __name__ == "__main__":
    matches = check_authors_in_startups()
    print(f"\nTotal matches: {len(matches)}")
