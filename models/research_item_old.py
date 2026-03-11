"""
Réceptacle central des publications académiques.

Features:
- Identification unique par DOI (pivot) et external_id (source).
- Stockage des métadonnées textuelles (titre, abstract) et temporelles.
- Gestion des thématiques via keywords et topics (JSON).
- Traçabilité complète via le champ raw pour l'audit des données hétérogènes.
"""

from typing import Optional, Dict, List
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

class ResearchItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="source.id", index=True)
    external_id: str = Field(index=True)  # ID source (OpenAlex, arXiv)
    
    # Pivot d'unicité
    doi: Optional[str] = Field(default=None, unique=True, index=True)
    
    # Contenu
    title: Optional[str] = None
    abstract: Optional[str] = None
    year: Optional[int] = Field(default=None, index=True)
    publication_date: Optional[datetime] = None
    
    # Métadonnées
    type: Optional[str] = None  # paper, preprint, article
    language: Optional[str] = None
    is_retracted: bool = Field(default=False)
    is_open_access: Optional[bool] = None
    license: Optional[str] = None
    url: Optional[str] = None
    citation_count: Optional[int] = Field(default=0)
    
    # Taxonomies
    keywords: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    topics: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    
    # Audit et Maintenance
    raw: Optional[Dict] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)