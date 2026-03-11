from sqlmodel import Session
from database import engine
from crawlers.open_alex_crawler import crawl_openalex_ai
from processors.openalex_processor import OpenAlexProcessor

def run_test():
    print("=== ÉTAPE 1 : CRAWL OPENALEX (API) ===")
    # Ton crawler récupère les données
    works = crawl_openalex_ai()
    
    if not works:
        print("Aucun article trouvé.")
        return

    print(f"\n=== ÉTAPE 2 : INGESTION (LIMITÉ À 10) ===")
    with Session(engine) as session:
        processor = OpenAlexProcessor(session)
        # On ne traite que les 10 premiers pour le test rapide
        count = processor.process_works(works[:10])
        print(f"Succès : {count} nouveaux articles insérés.")

if __name__ == "__main__":
    run_test()