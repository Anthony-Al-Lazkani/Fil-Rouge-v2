#!/usr/bin/env python3
"""
Pipeline script to crawl data from OpenAlex, arXiv, Semantic Scholar, and HAL and insert into database.
This script connects crawlers with processors to complete the data flow.
"""

import argparse
from database.initialize import create_db_and_tables
from crawlers.open_alex_crawler import crawl_openalex_ai
from crawlers.arxiv_crawler import crawl_ai_articles
from crawlers.semantic_scholar_crawler import crawl_semantic_scholar_ai
from crawlers.hal_crawler import crawl_hal_ai
from processors.openalex_processor import OpenAlexProcessor
from processors.arxiv_processor import ArxivProcessor
from processors.semantic_scholar_processor import SemanticScholarProcessor
from processors.hal_processor import HalProcessor


def run_openalex_pipeline():
    """Run OpenAlex crawling and processing pipeline"""
    print("=== Running OpenAlex Pipeline ===")

    # 1. Crawl the data
    print("Crawling OpenAlex data...")
    works = crawl_openalex_ai()
    print(f"Crawled {len(works)} works from OpenAlex")

    # 2. Process and insert into database
    print("Processing and inserting into database...")
    processor = OpenAlexProcessor()
    processed_count = processor.process_works(works)
    print(f"Successfully processed {processed_count} OpenAlex works")

    return processed_count


def run_arxiv_pipeline():
    """Run arXiv crawling and processing pipeline"""
    print("=== Running arXiv Pipeline ===")

    # 1. Crawl the data
    print("Crawling arXiv data...")
    articles = crawl_ai_articles()
    print(f"Crawled {len(articles)} articles from arXiv")

    print("Processing and inserting into database...")
    processor = ArxivProcessor()
    processed_count = processor.process_articles(articles)
    print(f"Successfully processed {processed_count} arXiv articles")

    return processed_count


def run_semantic_scholar_pipeline():
    """Run Semantic Scholar crawling and processing pipeline"""
    print("=== Running Semantic Scholar Pipeline ===")

    # 1. Crawl the data
    print("Crawling Semantic Scholar data...")
    records = crawl_semantic_scholar_ai()
    print(f"Crawled {len(records)} records from Semantic Scholar")

    # 2. Process and insert into database
    print("Processing and inserting into database...")
    processor = SemanticScholarProcessor()
    processed_count = processor.process_records(records)
    print(f"Successfully processed {processed_count} Semantic Scholar records")

    return processed_count


def run_hal_pipeline():
    """Run HAL crawling and processing pipeline"""
    print("=== Running HAL Pipeline ===")

    # 1. Crawl the data
    print("Loading HAL data...")
    records = crawl_hal_ai()
    print(f"Loaded {len(records)} records from HAL")

    # 2. Process and insert into database
    print("Processing and inserting into database...")
    processor = HalProcessor()
    processed_count = processor.process_records(records)
    print(f"Successfully processed {processed_count} HAL records")

    return processed_count


def main():
    parser = argparse.ArgumentParser(
        description="Run data crawling and processing pipelines"
    )
    parser.add_argument(
        "--source",
        choices=["openalex", "arxiv", "semantic_scholar", "hal", "all"],
        default="all",
        help="Which source to process (default: all)",
    )

    args = parser.parse_args()

    # Initialize database
    print("Initializing database...")
    create_db_and_tables()

    total_processed = 0

    if args.source in ["openalex", "all"]:
        total_processed += run_openalex_pipeline()
        print()

    if args.source in ["arxiv", "all"]:
        total_processed += run_arxiv_pipeline()
        print()

    if args.source in ["semantic_scholar", "all"]:
        total_processed += run_semantic_scholar_pipeline()
        print()

    if args.source in ["hal", "all"]:
        total_processed += run_hal_pipeline()
        print()

    print(f"=== Pipeline Complete ===")
    print(f"Total items processed: {total_processed}")


if __name__ == "__main__":
    main()
