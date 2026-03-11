"""
Cette table va enregistrer chaque relation unique. Elle répond à la question : "Qui travaillait où pour quel article ?"
Conçu pour faciliter la construction d'ontologies.
"""

from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class Affiliation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # =====================
    # RESEARCH ITEM INFO
    # =====================
    research_item_id: int = Field(foreign_key="researchitem.id", index=True)
    research_item_external_id: str  # OpenAlex, arXiv, etc.
    research_item_doi: Optional[str] = None
    research_item_title: Optional[str] = None
    research_item_year: Optional[int] = None
    research_item_source: Optional[str] = None  # openalex, arxiv, etc.

    # =====================
    # AUTHOR INFO
    # =====================
    author_external_id: str = Field(index=True)  # OpenAlex ID, ORCID, etc.
    author_full_name: Optional[str] = None
    author_orcid: Optional[str] = None

    # =====================
    # ENTITY INFO (unified: company, institution, research_lab, etc.)
    # =====================
    entity_id: Optional[int] = Field(foreign_key="entity.id", nullable=True, index=True)
    entity_name: Optional[str] = None
    entity_type: Optional[str] = (
        None  # company, institution, research_lab, university, etc.
    )
    entity_external_id: Optional[str] = Field(index=True)
    entity_ror: Optional[str] = Field(index=True)
    entity_country_code: Optional[str] = None

    # =====================
    # ADDITIONAL AFFILIATION INFO
    # =====================
    role: Optional[str] = None  # first_author, corresponding_author, co_author
    raw_affiliation_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
