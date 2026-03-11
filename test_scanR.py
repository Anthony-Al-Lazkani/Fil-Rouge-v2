from sqlmodel import Session
from database import engine
from crawlers.scanR_crawler import crawl_scanr_ai
from processors.scanR_processor import ScanRProcessor

def run_test():
    print("=== ÉTAPE 1 : CRAWL SCANR (LÉGER) ===")
    # On limite à 1 page (20 résultats) pour le test
    orgs = crawl_scanr_ai(query="intelligence artificielle", max_pages=1)
    
    if not orgs:
        print("Rien trouvé sur ScanR.")
        return

    print(f"\n=== ÉTAPE 2 : INGESTION DE {len(orgs)} ORGANISATIONS ===")
    with Session(engine) as session:
        processor = ScanRProcessor(session)
        count = processor.process_organizations(orgs)
        print(f"Succès : {count} entrées ScanR traitées.")

if __name__ == "__main__":
    run_test()