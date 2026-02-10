"""
Table de jointure entre ResearchItem et FieldOfStudy.
Permet d'associer plusieurs domaines de recherche à un article académique et de lister les articles en fonction d'un domaine
"""
from typing import Optional
from sqlmodel import SQLModel, Field

class ResearchItemField(SQLModel, table=True):
    # Clé primaire
    id: Optional[int] = Field(default=None, primary_key=True)

    # Clés étrangères
    research_item_id: int = Field(foreign_key="research_item.id", index=True)
    field_of_study_id: int = Field(foreign_key="fieldofstudy.id", index=True)
