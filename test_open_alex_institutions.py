from sqlmodel import Session, select
from database import engine
from models import Entity
from crawlers.open_alex_institution_crawler import crawl_openalex_institutions
from processors.open_alex_institution_processor import OpenAlexInstitutionProcessor

def run_test():
    print("=== TEST DÉDIÉ : OPENALEX INSTITUTIONS ===")
    
    # 1. Crawl (Limite à 10 pour le test)
    print("\n[1/2] Crawl en cours...")
    raw_data = crawl_openalex_institutions(limit=10)
    
    if not raw_data:
        print("Erreur : Aucun article récupéré via le crawler.")
        return
    print(f"-> {len(raw_data)} items récupérés.")

    # 2. Ingestion
    print("\n[2/2] Ingestion en base...")
    with Session(engine) as session:
        processor = OpenAlexInstitutionProcessor(session)
        count = processor.process_institutions(raw_data)
        print(f"-> {count} nouvelles institutions insérées dans la table Entity.")

        # 3. Vérification visuelle
        print("\n=== APERÇU DES 5 DERNIÈRES ENTITÉS ===")
        entities = session.exec(select(Entity).order_by(Entity.id.desc()).limit(5)).all()
        for e in entities:
            print(f"Nom: {e.name[:30]:<30} | ROR: {e.ror} | Pays: {e.country_code}")

if __name__ == "__main__":
    run_test()