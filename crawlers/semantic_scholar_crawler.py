import json
import time
from pathlib import Path
from datetime import datetime
from .semantic_scholar_fetcher import SemanticScholarFetcher
from typing import List, Dict, Any


def crawl_semantic_scholar_ai() -> List[Dict[str, Any]]:
    """
    Crawl Semantic Scholar for AI-related papers.
    Returns a list of processed records ready for database insertion.
    """
    # Configuration
    QUERIES = [
        "artificial intelligence",
    ]
    YEARS = list(range(2026, 2027))  # 2026 only
    MAX_PER_YEAR = 2500
    API_KEY = "BJxxqhUWGI2QmwHvezhLqasQc0I3Sq2e5HrdxnCi"

    # Load existing IDs to avoid duplicates
    existing_ids = load_existing_ids()

    # Initialize fetcher
    fetcher = SemanticScholarFetcher(api_key=API_KEY, limit=100)

    all_records = []
    total_new = 0
    total_duplicates = 0

    print(f"Starting Semantic Scholar crawl...")
    print(f"Queries: {len(QUERIES)} queries")
    print(f"Years: {YEARS[0]}-{YEARS[-1]}")

    for query_idx, query in enumerate(QUERIES, 1):
        print(f"QUERY {query_idx}/{len(QUERIES)}: {query}")

        for year in YEARS:
            print(f"YEAR {year}")

            count = 0
            offset = 0
            consecutive_empty = 0

            while count < MAX_PER_YEAR and consecutive_empty < 3:
                try:
                    # Fetch with year filter
                    papers = fetcher.fetch(
                        query, year_min=year, year_max=year, offset=offset
                    )

                    if not papers:
                        consecutive_empty += 1
                        if consecutive_empty >= 3:
                            print(f"End of results (offset: {offset})")
                            break
                        offset += fetcher.limit
                        continue

                    consecutive_empty = 0

                    # Process each paper
                    for paper in papers:
                        paper_id = paper.get("paperId")

                        if not paper_id:
                            continue

                        # Check if already crawled
                        if paper_id in existing_ids:
                            total_duplicates += 1
                            continue

                        # New paper
                        existing_ids.add(paper_id)
                        count += 1
                        total_new += 1

                        # Build record for processing
                        record = {
                            "publication": {
                                "id": paper_id,
                                "title": paper.get("title"),
                                "year": paper.get("year"),
                                "venue": paper.get("venue"),
                                "citation_count": paper.get("citationCount", 0),
                                "url": paper.get("url"),
                                "doi": paper.get("externalIds", {}).get("DOI"),
                                "abstract": paper.get("abstract"),
                                "language": paper.get("language"),
                                "type": paper.get("type", "paper"),
                                "external_ids": paper.get("externalIds", {}),
                            },
                            "authors": [
                                {
                                    "id": author.get("authorId"),
                                    "name": author.get("name"),
                                    "orcid": author.get("orcid"),
                                    "affiliations": author.get("affiliations", []),
                                }
                                for author in paper.get("authors", [])
                            ],
                            "fields_of_study": paper.get("fieldsOfStudy", []),
                        }

                        all_records.append(record)

                        # Progress display
                        if count % 100 == 0:
                            print(f"   {year} | {count:,} new | offset: {offset}")

                    # Move to next batch
                    offset += fetcher.limit

                    # Pause for API rate limit
                    time.sleep(0.1)

                except Exception as e:
                    print(f"Error at offset {offset}: {e}")
                    offset += fetcher.limit
                    time.sleep(1)
                    continue

            print(f"{year} completed: {count:,} new papers")

    print(f"Semantic Scholar crawl completed:")
    print(f"{total_new:,} new papers")
    print(f"{total_duplicates:,} duplicates skipped")

    return all_records


def load_existing_ids(data_folder="../data") -> set:
    """Load all existing paper IDs from JSONL files"""
    existing_ids = set()
    data_path = Path(__file__).parent.parent / data_folder

    if not data_path.exists():
        return existing_ids

    jsonl_files = list(data_path.glob("semantic_scholar_*.jsonl"))

    for filepath in jsonl_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        paper_id = record.get("publication", {}).get("id")
                        if paper_id:
                            existing_ids.add(paper_id)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    return existing_ids
