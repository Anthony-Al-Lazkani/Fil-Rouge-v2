from pathlib import Path
from sqlmodel import Session
from database.initialize import engine, create_db_and_tables # Import engine aussi
from processors.organization_processor import OrganizationProcessor
import os

data_path = Path("data")

files = [
    "AI_Companies.csv",
    "Startup-Dataset.csv",
    "Startups-in-2021-end.csv",
    "Crunchbase_csv.csv"
]



# 1. Reset
if os.path.exists("database.db"):
    os.remove("database.db")

# 2. Init
create_db_and_tables()

# 3. Utilisation d'un bloc 'with' pour la session
with Session(engine) as session:
    data_path = Path("data")
    processor = OrganizationProcessor(session=session, data_dir=data_path)

    print("Ingestion Crunchbase...")
    c1 = processor.process_crunchbase_csv()
    
    print("Ingestion AI Companies...")
    c2 = processor.process_ai_companies()

    print("Ingestion startup_dataset.csv...")
    c3 = processor.process_startup_dataset()

    print("Ingestion startups-in-2021.csv...")
    c4 = processor.process_startups_2021()

    # CRUCIAL : On valide TOUTES les insertions de la session d'un coup
    session.commit() 
    
    print(f"Crunchbase: {c1}")
    print(f"AI Companies: {c2}")
    print(f"startups: {c3}")
    print(f"2021 startups: {c4}")
    
