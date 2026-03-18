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
from crawlers.inpi_crawler import InpiCrawler
from processors.inpi_processor import InpiProcessor 

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
    parser.add_argument("--limit", type=int, default=100, help="Nombre max d'items à récupérer")
    parser.add_argument("--year", type=int, default=2022, help="Année de départ pour la collecte")
    parser.add_argument("--query", default="intelligence artificielle", help="Mot-clé de recherche")

    args = parser.parse_args()

    print("Initializing database...")
    create_db_and_tables()

    total_processed = 0
    s = args.source
    limit = args.limit
    year = args.year
    query = args.query

    # Traduction de la query pour les sources anglophones
    query_en = "artificial intelligence" if query == "intelligence artificielle." else query

    with Session(engine) as session:
        # 0. Bases Locales (Crunchbase, AI Companies, etc.)
        if s in ["local", 'csv', "all"]:
            print("=== Running Local Databases Pipeline ===")
            data_dir = Path("data") # Dossier où sont tes CSV
            if data_dir.exists():
                local_processor = local_processor = OrganizationProcessor(session, data_dir)
                
                # On lance les différentes méthodes du processeur
                count = 0
                count += local_processor.process_crunchbase_csv()
                count += local_processor.process_ai_companies()
                count += local_processor.process_startups_2021()
                
                print(f"Successfully processed {count} local items\n")
                total_processed += count
            else:
                print("Dossier /data non trouvé. Skip local ingestion.\n")

        # 1. OpenAlex
        if s in ["openalex", "all"]:
            print(f"=== Running OpenAlex Pipeline (Limit: {limit}, Year: {year}) ===")
            data = crawl_openalex_ai(max_articles=limit, from_year=year, to_year=2026)
            total_processed += run_source("openalex", session, data, OpenAlexProcessor, "process_works")
    
        # 2. OpenAlex Institutions / augmentation de la limite ici
        if s in ["openalex_inst", 'open_alex_institution', "all"]:
            print(f"=== Running OpenAlex Institutions Pipeline (Limit: {limit}) ===")
            data = crawl_openalex_institutions(limit=limit)
            total_processed += run_source("openalex_inst", session, data, OpenAlexInstitutionProcessor, "process_institutions")

       # 3. ArXiv / max_results pour chaque catégorie d'articles / from_year: récupère de 2026 jusqu'à "from_year"
        if s in ["arxiv", "all"]:
            print(f"=== Running ArXiv Pipeline (Limit/Cat: {limit}, Year: {year}) ===")
            data = crawl_ai_articles(max_results_per_cat=limit, from_year=year)
            total_processed += run_source("arxiv", session, data, ArxivProcessor, "process_articles")

        # 4. Semantic Scholar (CLASSE avec arguments)
        if s in ["semantic_scholar", 's2', "all"]:
            print(f"=== Running Semantic Scholar Pipeline (Limit: {limit}) ===")
            key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
            crawler = SemanticScholarCrawler(api_key=key)
            data = crawler.fetch_ai_papers(query=query_en, year=2022, max_results=limit)
            if data:
                proc = SemanticScholarProcessor(session)
                count = proc.process_papers(data)
                total_processed += count
                print(f"Processed {count} items\n")

        # 5. HAL (CLASSE avec arguments) / contrôle sur la date de début et le max / attention HAL fournit les articles par ordre de pertinence et non par date
        if s in ["hal", "all"]:
            print(f"=== Running HAL Pipeline (Query: {query}, Year: {year}) ===")
            try:
                crawler = HALCrawler()
                data = crawler.fetch_ai_publications(query=query, start_year=year, max_results=limit)
                total_processed += run_source("hal", session, data, HalProcessor, "process_records")
            except Exception as e:
                print(f"[ERROR] HAL failed: {e}")

        # 6. ScanR / contrôle de la limite ici
        if s in ["scanr", "all"]:
            print(f"=== Running ScanR Pipeline (Query: {query}, Limit: {limit}) ===")
            data = crawl_scanr_ai(query=query, limit=limit)
            total_processed += run_source("scanr", session, data, ScanRProcessor, "process_organizations")

        # 7. INPI / EPO / contrôle sur la date la plus ancienne et sur le nombre de résultats max / attention, ne fonctionne que pendant 20min
        if s in ["inpi", 'epo', "all"]:
            print(f"=== Running INPI Pipeline (Query: {query_en}, Year: {year}) ===")
            client_id = os.getenv("EPO_CLIENT_ID")
            client_secret = os.getenv("EPO_CLIENT_SECRET")
            crawler = InpiCrawler(client_id, client_secret)
            data = crawler.fetch_ai_patents(query_text=query_en, max_results=limit, from_year=year)
            if data:
                proc = InpiProcessor(session)
                count = proc.process_patents(data)
                total_processed += count
                print(f"Processed {count} items\n")
        
          
        # 8. OpenCorporates / pas de contrôle sur l'année ici, seulement sur le volume
        if s in ["open_corporates", "all"]:
            print(f"=== Running Open Corporates Pipeline (Query: {query_en}, Limit: {limit}) ===")
            data = crawl_opencorporates_ai(limit=limit, query=query_en)
            total_processed += run_source("open_corporates", session, data, OpenCorporatesProcessor, "process_companies")

        

    print(f"=== Pipeline Complete ===\nTotal items processed: {total_processed}")

if __name__ == "__main__":
    main()