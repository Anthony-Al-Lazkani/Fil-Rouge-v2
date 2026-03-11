"""
Initialisation et configuration de la base de données SQLite.
Indispensable. C'est le fondement technique. Sans lui, la base de données n'existe pas physiquement et les tables ne sont pas créées.

Features:
- Définition de l'URL de connexion et de l'engine SQLModel.
- Création physique du fichier database.db et des tables à partir des modèles.
- Point d'entrée pour la mise à jour de la structure (schéma) de la BDD.

A relancer à chaque modif de la structure de la BDD
uv run python -m database.initialize
"""

from sqlmodel import create_engine, SQLModel
from models.source import Source
from models.research_item import ResearchItem
from models.author import Author
from models.affiliation import Affiliation
from models.entity import Entity
from models.organization import Organization  # Deprecated
from models.institution import Institution  # Deprecated

# Arguments needed in order to create the engine
FILENAME = "database.db"
SQLITEURL = f"sqlite:///{FILENAME}"
connect_args = {"check_same_thread": False}

# Create the engine
engine = create_engine(SQLITEURL, connect_args=connect_args)


# Function in order to initialize the database and the tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
