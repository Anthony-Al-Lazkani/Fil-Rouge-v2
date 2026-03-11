#!/usr/bin/env python3
import argparse
import sys
import os
from sqlmodel import Session

from pathlib import Path
# Gestion des chemins
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.initialize import create_db_and_tables
from database import engine

# Crawlers
from crawlers.open_alex_crawler import crawl_openalex_ai
from crawlers.open_alex_institution_crawler import crawl_openalex_institutions
from crawlers.arxiv_crawler import crawl_ai_articles
from crawlers.semantic_scholar_crawler import SemanticScholarCrawler
from crawlers.hal_crawler import HALCrawler
from crawlers.scanR_crawler import crawl_scanr_ai
from crawlers.open_corporates_crawler import crawl_opencorporates_ai

# Processors
from processors.openalex_processor import OpenAlexProcessor
from processors.open_alex_institution_processor import OpenAlexInstitutionProcessor
from processors.arxiv_processor import ArxivProcessor
from processors.semantic_scholar_processor import SemanticScholarProcessor
from processors.hal_processor import HalProcessor
from processors.scanR_processor import ScanRProcessor
from processors.open_corporates_processor import OpenCorporatesProcessor
from processors.organization_processor import OrganizationProcessor

def run_source(name, session, data, processor_class, process_method):
    """Gère l'ingestion une fois que les données sont récupérées."""
    if not data:
        print(f"No data retrieved for {name}.\n")
        return 0
    
    print(f"Crawled {len(data)} items from {name}")
    processor = processor_class(session)
    count = getattr(processor, process_method)(data)
    print(f"Successfully processed {count} {name} items\n")
    return count

def main():
    parser = argparse.ArgumentParser(description="Run data crawling and processing pipelines")
    parser.add_argument("--source", default="all", help="Source à traiter")
    args = parser.parse_args()

    print("Initializing database...")
    create_db_and_tables()

    total_processed = 0
    s = args.source

    with Session(engine) as session:
        # 0. Bases Locales (Crunchbase, AI Companies, etc.)
        if s in ["local", "all"]:
            print("=== Running Local Databases Pipeline ===")
            data_dir = Path("data") # Dossier où sont tes CSV
            if data_dir.exists():
                local_processor = local_processor = OrganizationProcessor(session, data_dir)
                
                # On lance les différentes méthodes du processeur
                count = 0
                count += local_processor.process_crunchbase_csv()
                count += local_processor.process_ai_companies()
                count += local_processor.process_startup_dataset()
                count += local_processor.process_startups_2021()
                
                print(f"Successfully processed {count} local items\n")
                total_processed += count
            else:
                print("Dossier /data non trouvé. Skip local ingestion.\n")

        # 1. OpenAlex
        if s in ["openalex", "all"]:
            print("=== Running OpenAlex Pipeline ===")
            data = crawl_openalex_ai()
            total_processed += run_source("openalex", session, data, OpenAlexProcessor, "process_works")
    
        # 2. OpenAlex Institutions
        if s in ["openalex_inst", "all"]:
            print("=== Running OpenAlex Inst Pipeline ===")
            data = crawl_openalex_institutions()
            total_processed += run_source("openalex_inst", session, data, OpenAlexInstitutionProcessor, "process_institutions")

        # 3. ArXiv
        if s in ["arxiv", "all"]:
            print("=== Running ArXiv Pipeline ===")
            data = crawl_ai_articles()
            total_processed += run_source("arxiv", session, data, ArxivProcessor, "process_articles")

        # 4. Semantic Scholar (CLASSE avec arguments)
        if s in ["semantic_scholar", "all"]:
            print("=== Running Semantic Scholar Pipeline ===")
            try:
                crawler = SemanticScholarCrawler()
                data = crawler.fetch_ai_papers(query="intelligence artificielle", year=2024, max_results=10)
                total_processed += run_source("semantic_scholar", session, data, SemanticScholarProcessor, "process_papers")
            except Exception as e:
                print(f"[ERROR] Semantic Scholar failed: {e}")

        # 5. HAL (CLASSE avec arguments)
        if s in ["hal", "all"]:
            print("=== Running HAL Pipeline ===")
            try:
                crawler = HALCrawler()
                data = crawler.fetch_ai_publications(query="intelligence artificielle", start_year=2024, max_results=10)
                total_processed += run_source("hal", session, data, HalProcessor, "process_records")
            except Exception as e:
                print(f"[ERROR] HAL failed: {e}")

        # 6. ScanR
        if s in ["scanr", "all"]:
            print("=== Running ScanR Pipeline ===")
            data = crawl_scanr_ai()
            total_processed += run_source("scanr", session, data, ScanRProcessor, "process_organizations")

        # 7. OpenCorporates
        if s in ["open_corporates", "all"]:
            print("=== Running Open Corporates Pipeline ===")
            data = crawl_opencorporates_ai()
            total_processed += run_source("open_corporates", session, data, OpenCorporatesProcessor, "process_companies")

        

    print(f"=== Pipeline Complete ===\nTotal items processed: {total_processed}")

if __name__ == "__main__":
    main()