"""
Script de test du pipeline HAL.
Enchaîne le crawl léger et l'ingestion en base de données.
"""

from sqlmodel import Session
from database import engine
from crawlers.hal_crawler import HALCrawler
from processors.hal_processor import HalProcessor

def run_test():
    
    # 1. Collecte des données (Mode léger : 10 articles)
    print("=== ÉTAPE 1 : CRAWL HAL (MODE LÉGER) ===")
    crawler = HALCrawler(rows=10)
    # On cherche un terme précis pour garantir des résultats rapides
    docs = crawler.fetch_ai_publications(
        query='"intelligence artificielle"', 
        start_year=2024, 
        max_results=10
    )
    
    if not docs:
        print("Aucun document récupéré. Vérifiez l'API HAL ou votre connexion.")
        return

    # 2. Ingestion en base de données
    print(f"\n=== ÉTAPE 2 : INGESTION DE {len(docs)} DOCUMENTS ===")
    with Session(engine) as session:
        processor = HalProcessor(session)
        new_items_count = processor.process_records(docs)
        print(f"Succès : {new_items_count} nouvelles notices HAL insérées en base.")

if __name__ == "__main__":
    run_test()