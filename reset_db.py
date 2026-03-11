import os
from pathlib import Path
from sqlmodel import SQLModel # Import direct depuis la bibliothèque
from database import engine
import models # Importe te

def reset_database():
    db_path = Path("database.db")
    if db_path.exists():
        os.remove(db_path)
        print("Fichier database.db supprimé.")
    
    print("Création des tables...")
    SQLModel.metadata.create_all(engine)
    print("Base de données réinitialisée avec succès.")

if __name__ == "__main__":
    reset_database()