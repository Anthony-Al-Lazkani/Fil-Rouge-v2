"""
Script de test du pipeline ArXiv.
Enchaîne le crawl léger et l'ingestion en base de données.
"""

from sqlmodel import Session
from database import engine
from crawlers.arxiv_crawler import crawl_ai_articles
from processors.arxiv_processor import ArxivProcessor

def run_test():
    # 1. Collecte des données (Crawl léger défini dans tes constantes)
    print("=== ÉTAPE 1 : CRAWL ARXIV ===")
    articles = crawl_ai_articles()
    
    if not articles:
        print("Aucun article récupéré. Vérifiez votre connexion ou les catégories.")
        return

    # 2. Ingestion en base de données
    print(f"\n=== ÉTAPE 2 : INGESTION DE {len(articles)} ARTICLES ===")
    with Session(engine) as session:
        processor = ArxivProcessor(session)
        new_items_count = processor.process_articles(articles)
        print(f"Succès : {new_items_count} nouveaux articles insérés en base.")

if __name__ == "__main__":
    run_test()