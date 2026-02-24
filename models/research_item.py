"définit la structure de la table ResearchItem (réceptacle des crawler académiques)"

"Attention: doi : unique=true"


from typing import Optional, Dict, List
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class ResearchItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int  # FK to Source table
    external_id: str  # ID from the source (OpenAlex, arXiv, etc.)
    doi: Optional[str] = Field(default=None, unique=True, index=True)
    title: Optional[str]
    abstract: Optional[str]
    year: Optional[int]
    publication_date: Optional[datetime]
    type: Optional[str]  # paper, preprint, article
    language: Optional[str]
    is_retracted: bool = False
    is_open_access: Optional[bool]
    license: Optional[str]
    url: Optional[str]  # landing page URL
    citation_count: Optional[int] = Field(default=0)
    keywords: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    topics: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    metrics: Optional[Dict] = Field(default_factory=dict, sa_column=Column(JSON))
    raw: Optional[Dict] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
