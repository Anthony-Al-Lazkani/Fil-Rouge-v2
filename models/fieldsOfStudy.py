"""
Table des domaines de recherche (Fields of Study).
Contient les informations sur les domaines académiques avec leurs identifiants
Wikidata et catégories ArXiv.
"""
from typing import Optional
from sqlmodel import SQLModel, Field

class FieldOfStudy(SQLModel, table=True):
    # Clé primaire
    id: Optional[int] = Field(default=None, primary_key=True)

    # Informations du domaine
    domaine: Optional[str]  # Nom en français
    field: str  # Nom en anglais
    wikidata_id: Optional[str] = Field(default=None, index=True)
    arxiv_category: Optional[str] = Field(default=None, index=True)
