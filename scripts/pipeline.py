#!/usr/bin/env python3
"""
Pipeline script to crawl data from OpenAlex, arXiv, Semantic Scholar, and HAL and insert into database.
This script connects crawlers with processors to complete the data flow.
"""

import argparse
from database.initialize import create_db_and_tables
from crawlers.open_alex_crawler import crawl_openalex_ai
from crawlers.open_alex_institution_crawler import crawl_openalex_institutions
from crawlers.arxiv_crawler import crawl_ai_articles
from crawlers.semantic_scholar_crawler import crawl_semantic_scholar_ai
from crawlers.hal_crawler import crawl_hal_ai
from processors.openalex_processor import OpenAlexProcessor
from processors.institution_processor import InstitutionProcessor
from processors.affiliation_processor import AffiliationProcessor
from processors.arxiv_processor import ArxivProcessor
from processors.semantic_scholar_processor import SemanticScholarProcessor
from processors.hal_processor import HalProcessor
from crawlers.scanR_crawler import crawl_scanr_ai
from processors.scanR_processor import ScanRProcessor
from crawlers.open_corporates_crawler import crawl_opencorporates_ai
from processors.open_corporates_processor import OpenCorporatesProcessor


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


def run_openalex_institution_pipeline():
    """Run OpenAlex institution crawling and processing pipeline"""
    print("=== Running OpenAlex Institution Pipeline ===")

    # 1. Crawl the data
    print("Crawling OpenAlex institutions...")
    institutions = crawl_openalex_institutions()
    print(f"Crawled {len(institutions)} institutions from OpenAlex")

    # 2. Process and insert into database
    print("Processing and inserting into database...")
    processor = InstitutionProcessor()
    processed_count = processor.process_institutions(institutions)
    print(f"Successfully processed {processed_count} OpenAlex institutions")

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

def run_scanr_pipeline():
    print("=== Running ScanR Pipeline ===")
    orgs = crawl_scanr_ai()
    processor = ScanRProcessor()
    count = processor.process_organizations(orgs)
    print(f"Successfully processed {count} ScanR organizations")
    return count


def run_open_corporates_pipeline():
    print("=== Running Open Corporates Pipeline ===")
    
    # 1. On récupère les données (limité à 10 pour le POC dans le crawler)
    companies = crawl_opencorporates_ai()
    
    # 2. On initialise le processor spécifique
    processor = OpenCorporatesProcessor()
    
    # 3. On insère en base
    count = processor.process_companies(companies)
    
    print(f"Successfully processed {count} OpenCorporates organizations")
    return count




def run_affiliation_pipeline():
    """Run affiliation processing pipeline"""
    print("=== Running Affiliation Pipeline ===")

    print("Processing affiliations from research items...")
    processor = AffiliationProcessor()
    processed_count = processor.process_all_research_items()
    print(f"Successfully processed {processed_count} affiliations")

    return processed_count


def main():
    parser = argparse.ArgumentParser(
        description="Run data crawling and processing pipelines"
    )
    parser.add_argument(
        "--source",
        choices=["openalex", "arxiv", "semantic_scholar", "hal", "scanr", "open_corporates", "all"],
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

    if args.source in ["openalex_institutions", "all"]:
        total_processed += run_openalex_institution_pipeline()
        print()

    if args.source in ["affiliations", "all"]:
        total_processed += run_affiliation_pipeline()
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
    
    if args.source in ["scanr", "all"]:
        total_processed += run_scanr_pipeline()
        print()
    
    if args.source in ["open_corporates", "all"]:
        total_processed += run_open_corporates_pipeline()
        print()

    print(f"=== Pipeline Complete ===")
    print(f"Total items processed: {total_processed}")


if __name__ == "__main__":
    main()
