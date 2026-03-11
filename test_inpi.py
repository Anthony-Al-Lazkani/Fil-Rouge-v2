import os
from dotenv import load_dotenv
from sqlmodel import Session
from database import engine
from crawlers.inpi_crawler import InpiCrawler
from processors.inpi_processor import InpiProcessor

load_dotenv()

def run_test():
    client_id = os.getenv("EPO_CLIENT_ID")
    client_secret = os.getenv("EPO_CLIENT_SECRET")
    
    print("=== ÉTAPE 1 : CRAWL EPO OPS (5 BREVETS) ===")
    crawler = InpiCrawler(client_id, client_secret)
    patents = crawler.fetch_ai_patents(max_results=5)
    
    if not patents:
        print("Aucun brevet récupéré.")
        return

    print(f"\n=== ÉTAPE 2 : INGESTION DE {len(patents)} BREVETS ===")
    with Session(engine) as session:
        processor = InpiProcessor(session)
        count = processor.process_patents(patents)
        print(f"Succès : {count} brevets insérés.")

if __name__ == "__main__":
    run_test()