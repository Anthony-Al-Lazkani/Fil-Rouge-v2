# schemas/research_item.py
"""
Schémas Pydantic pour les Research Items.
Définit les structures de données pour la création et validation des articles de recherche.
"""
from typing import Optional, Dict, List
from pydantic import BaseModel

class ResearchItemCreate(BaseModel):
    source_id: int
    external_id: str
    doi: Optional[str] = None
    type: str  # "article", "company", etc.
    title: Optional[str]
    year: Optional[int]
    abstract: Optional[str] = None
    is_retracted: Optional[bool] = False
    is_open_access: Optional[bool] = None
    references: Optional[List[str]] = []  # Liste de DOIs ou IDs
    metrics: Optional[Dict] = {}
    raw: Optional[Dict] = {}
