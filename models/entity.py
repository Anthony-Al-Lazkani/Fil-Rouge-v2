"""
Structure unifiée pour les organisations académiques et les entreprises.

Features:
- Identification pivot via ROR (académique) et external_id (économique).
- Fusion des attributs de typage et de localisation.
- Support des métriques de performance : financement, publications et citations.
- Indicateurs spécifiques au domaine de l'IA (is_ai_related).
"""

from typing import Optional, List
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

class Entity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: Optional[int] = Field(default=None, foreign_key="source.id", index=True)
    external_id: Optional[str] = Field(default=None, index=True, unique=True)
    ror: Optional[str] = Field(default=None, index=True)

    # Hiérarchie - donnée par open_alex_institution notamment
    parent_id: Optional[int] = Field(default=None, foreign_key="entity.id", index=True, nullable=True)

    # Identité
    name: str = Field(index=True)
    display_name: Optional[str] = Field(default=None, index=True)
    acronyms: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    
    # Classification (Unifiée)
    type: Optional[str] = Field(default=None, index=True) # company, education, facility, etc.
    
    # Géographie
    country_code: Optional[str] = Field(default=None, index=True)
    city: Optional[str] = Field(default=None, index=True)
    
    # Web
    website: Optional[str] = None
    description: Optional[str] = None

    # Métriques Entreprise (Startup/Business)
    founded_date: Optional[str] = None
    industries: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    operating_status: Optional[str] = None # active, closed, ipo
    estimated_revenue: Optional[str] = None
    total_funding: Optional[float] = None
    valuation: Optional[float] = None
    last_funding_date: Optional[str] = None

    # Métriques Académiques
    works_count: Optional[int] = Field(default=0)
    cited_by_count: Optional[int] = Field(default=0)

    # Spécificité IA
    is_ai_related: Optional[bool] = Field(default=None, index=True)
    ai_focus_percent: Optional[int] = None

    # Audit
    raw: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSON))