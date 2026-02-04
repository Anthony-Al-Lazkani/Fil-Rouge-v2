'''
Pour avoir mieux qu'une liste de noms
'''
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from models import ResearchItem


class Author(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Identifiants pivots internationaux (ORCID, IdHAL, etc.)
    external_id: Optional[str] = Field(default=None, index=True, unique=True, description="ID externe (ORCID, IdHAL, etc.)")
    # unique=True sur les external_id => la base refusera techniquement de créer deux fois le même laboratoire ou le même auteur, même si vous les croisez dans des sources différentes
    
    full_name: str = Field(index=True)
    
    # Métriques simplifiées pour le profilage
    publication_count: int = Field(default=0)
    country: Optional[str] = Field(default=None, index=True, description="Pays de l'auteur")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relations
    # Liste des articles scientifiques écrits par cet auteur
    # - back_populates: Synchronise avec la relation 'authors' dans ResearchItem
    # - link_model: Utilise la table de jointure AuthorResearchItem pour stocker les associations
    articles: List["ResearchItem"] = Relationship(back_populates="authors",link_model="AuthorResearchItem")
