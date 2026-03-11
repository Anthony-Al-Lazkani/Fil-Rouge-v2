from sqlmodel import Session, select
from database import engine
from models import Entity
from crawlers.open_corporates_crawler import crawl_opencorporates_ai
from processors.open_corporates_processor import OpenCorporatesProcessor

def run_test():
    print("=== TEST : OPENCORPORATES (REGISTRE LÉGAL) ===")
    
    # 1. Crawl
    print("\n[1/2] Recherche de boîtes IA sur OpenCorporates...")
    companies = crawl_opencorporates_ai()
    
    if not companies:
        print("Erreur : Aucun résultat. Vérifie ta clé API dans le .env")
        return

    # 2. Ingestion
    print(f"\n[2/2] Ingestion de {len(companies)} entreprises...")
    with Session(engine) as session:
        processor = OpenCorporatesProcessor(session)
        count = processor.process_companies(companies)
        print(f"-> {count} nouvelles entreprises insérées.")

        # 3. Vérification
        print("\n=== DERNIÈRES ENTREPRISES LÉGALES ===")
        entities = session.exec(select(Entity).where(Entity.source_id == processor.source_id).limit(5)).all()
        for e in entities:
            print(f"Nom: {e.name[:30]:<30} | Pays: {e.country_code} | ID: {e.external_id}")

if __name__ == "__main__":
    run_test()