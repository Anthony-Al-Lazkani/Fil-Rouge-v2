import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = Path(__file__).parent / "database.db"


def load_semantic_scholar():
    """Load authors and research items from semantic scholar JSONL files."""
    print("Loading Semantic Scholar data...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    source_id = 1  # semantic_scholar
    now = datetime.utcnow().isoformat()

    count = 0
    author_count = 0

    jsonl_files = list(DATA_DIR.glob("semantic_scholar_*.jsonl"))
    for jsonl_file in jsonl_files:
        print(f"  Processing {jsonl_file.name}...")
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)

                    pub = data.get("publication", {})
                    doi = pub.get("doi")
                    title = pub.get("title")
                    abstract = pub.get("abstract")
                    year = pub.get("year")
                    ext_id = pub.get("id", "")
                    url = pub.get("url")
                    citation_count = pub.get("citation_count", 0)

                    if not ext_id:
                        ext_id = str(uuid.uuid4())

                    if title:
                        cur.execute(
                            """
                            INSERT INTO researchitem 
                            (source_id, external_id, doi, title, abstract, year, url, citation_count, is_retracted, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                        """,
                            (
                                source_id,
                                ext_id,
                                doi,
                                title,
                                abstract,
                                year,
                                url,
                                citation_count,
                                now,
                                now,
                            ),
                        )
                        count += 1

                    authors = data.get("authors", [])
                    for author in authors:
                        author_name = author.get("name")
                        if author_name and author_name.strip():
                            try:
                                cur.execute(
                                    """
                                    INSERT INTO author (full_name, publication_count)
                                    VALUES (?, 0)
                                """,
                                    (author_name.strip(),),
                                )
                                author_count += 1
                            except:
                                pass
                except:
                    pass

    conn.commit()
    conn.close()
    print(f"  Loaded {count} research items, {author_count} authors")
    return count


def load_openalex():
    """Load authors and research items from OpenAlex JSONL files."""
    print("Loading OpenAlex data...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    source_id = 2  # openalex
    now = datetime.utcnow().isoformat()

    count = 0
    author_count = 0

    jsonl_file = DATA_DIR / "openalex_ai_bulk.jsonl"
    if jsonl_file.exists():
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 10000:
                    break
                try:
                    data = json.loads(line)

                    doi = data.get("doi")
                    title = data.get("title") or data.get("display_name")
                    abstract = data.get("abstract")
                    year = data.get("publication_year")
                    ext_id = data.get("id", "")

                    if not ext_id:
                        ext_id = str(uuid.uuid4())

                    if title:
                        cur.execute(
                            """
                            INSERT INTO researchitem 
                            (source_id, external_id, doi, title, abstract, year, is_retracted, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                        """,
                            (source_id, ext_id, doi, title, abstract, year, now, now),
                        )
                        count += 1

                    authorships = data.get("authorships", [])
                    for auth in authorships:
                        author_data = auth.get("author", {})
                        author_name = author_data.get("display_name")
                        if author_name:
                            try:
                                cur.execute(
                                    """
                                    INSERT INTO author (full_name, publication_count)
                                    VALUES (?, 0)
                                """,
                                    (author_name,),
                                )
                                author_count += 1
                            except:
                                pass
                except:
                    pass

    conn.commit()
    conn.close()
    print(f"  Loaded {count} research items, {author_count} authors")
    return count


def load_hal():
    """Load authors and research items from HAL JSONL files."""
    print("Loading HAL data...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    source_id = 3  # hal
    now = datetime.utcnow().isoformat()

    count = 0
    author_count = 0

    jsonl_file = DATA_DIR / "hal_publications.jsonl"
    if jsonl_file.exists():
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)

                    title = data.get("title")
                    abstract = data.get("abstract")
                    year = (
                        data.get("publication_date", "")[:4]
                        if data.get("publication_date")
                        else None
                    )
                    ext_id = data.get("id", "")

                    if not ext_id:
                        ext_id = str(uuid.uuid4())

                    if title:
                        cur.execute(
                            """
                            INSERT INTO researchitem 
                            (source_id, external_id, title, abstract, year, is_retracted, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                        """,
                            (source_id, ext_id, title, abstract, year, now, now),
                        )
                        count += 1

                    authors = data.get("authors", [])
                    for author in authors:
                        author_name = author.get("fullName")
                        if author_name and author_name.strip():
                            try:
                                cur.execute(
                                    """
                                    INSERT INTO author (full_name, publication_count)
                                    VALUES (?, 0)
                                """,
                                    (author_name.strip(),),
                                )
                                author_count += 1
                            except:
                                pass
                except:
                    pass

    conn.commit()
    conn.close()
    print(f"  Loaded {count} research items, {author_count} authors")
    return count


def get_counts():
    """Get current table counts."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    tables = ["source", "researchitem", "organization", "author", "affiliation"]
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t}: {cur.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    print("Loading research data...")
    get_counts()

    load_semantic_scholar()
    load_openalex()
    load_hal()

    print("\nFinal counts:")
    get_counts()
