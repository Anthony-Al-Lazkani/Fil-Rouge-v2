'''
A relancer à chaque modif de la structure de la BDD
uv run python -m database.initialize
'''

from sqlmodel import create_engine, SQLModel
from models.source import Source
from models.research_item import ResearchItem

# Arguments needed in order to create the engine
FILENAME = "database.db"
SQLITEURL = F"sqlite:///{FILENAME}"
connect_args = {"check_same_thread": False}

# Create the engine
engine = create_engine(SQLITEURL, connect_args=connect_args)

# Function in order to initialize the database and the tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)



