'''
A relancer à chaque modif de la structure de la BDD
uv run python -m database.initialize
'''

from sqlmodel import create_engine, SQLModel
from models.source import Source
from models.fieldsOfStudy import FieldOfStudy
from models.researchItemField import ResearchItemField

# Arguments needed in order to create the engine
FILENAME = "database.db"
SQLITEURL = F"sqlite:///{FILENAME}"
connect_args = {"check_same_thread": False}

# Create the engine
engine = create_engine(SQLITEURL, connect_args=connect_args)

# Function in order to initialize the database and the tables
def create_db_and_tables():
    print("🔥 DEBUT DE LA CREATION DES TABLES...")
    SQLModel.metadata.create_all(engine)
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"✅ {len(tables)} tables creees : {', '.join(tables)}")


if __name__ == "__main__":
    print("🚀 Lancement de la creation de la base de donnees...")
    create_db_and_tables()
    print("✅ Terminé !")
