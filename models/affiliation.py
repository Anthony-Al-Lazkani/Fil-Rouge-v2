"""
Table de pivot gérant les relations entre auteurs, publications et organisations.

Features:
- Centralisation des liens (Foreign Keys) entre ResearchItem et Entity.
- Stockage du rôle spécifique de l'auteur pour chaque publication (ex: first_author).
- Utilisation d'identifiants pivots (DOI, external_id) pour faciliter les jointures.
- Conservation des données sources brutes via le champ JSON raw_affiliation_data.
"""

from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

class Affiliation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # --- LIENS TECHNIQUES (Pour la BDD) ---
    research_item_id: int = Field(foreign_key="researchitem.id", index=True)
    entity_id: Optional[int] = Field(foreign_key="entity.id", nullable=True, index=True)
    
    # --- IDENTIFIANTS MÉTIER (Pour l'Ontologie & Lisibilité) ---
    # Ces IDs permettent de comprendre la ligne sans faire de JOIN
    author_external_id: str = Field(index=True) # ex: "https://openalex.org/A123"
    entity_ror: Optional[str] = Field(default=None, index=True) # ID pivot mondial des orgs
    research_item_doi: Optional[str] = Field(default=None, index=True)

    # --- NATURE DE LA RELATION ---
    role: Optional[str] = None  # first_author, corresponding, etc.
    source_name: Optional[str] = None # Savoir d'où vient cette affiliation (openalex, arxiv)

    # --- DONNÉES BRUTES ---
    raw_affiliation_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))