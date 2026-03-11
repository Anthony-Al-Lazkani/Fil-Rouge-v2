from sqlmodel import Session
from database import engine
from crawlers.semantic_scholar_crawler import SemanticScholarCrawler
from processors.semantic_scholar_processor import SemanticScholarProcessor

def run_test():
    # Variables de ton pipeline léger
    API_KEY = "BJxxqhUWGI2QmwHvezhLqasQc0I3Sq2e5HrdxnCi"
    
    print("=== ÉTAPE 1 : CRAWL SEMANTIC SCHOLAR (10 PAPERS) ===")
    crawler = SemanticScholarCrawler(api_key=API_KEY)
    papers = crawler.fetch_ai_papers(query="artificial intelligence", year=2026, max_results=10)
    
    if not papers:
        print("Aucun article trouvé.")
        return

    print(f"\n=== ÉTAPE 2 : INGESTION DE {len(papers)} ARTICLES ===")
    with Session(engine) as session:
        processor = SemanticScholarProcessor(session)
        new_count = processor.process_papers(papers)
        print(f"Succès : {new_count} nouveaux articles insérés.")

if __name__ == "__main__":
    run_test()