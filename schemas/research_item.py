# schemas/research_item.pystarted th
from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel


class ResearchItemCreate(BaseModel):
    source_id: int
    external_id: str
    doi: Optional[str] = None
    type: str  # "article", "company", etc.
    title: Optional[str]
    abstract: Optional[str] = None
    year: Optional[int]
    publication_date: Optional[datetime] = None
    language: Optional[str] = None
    is_retracted: Optional[bool] = False
    is_open_access: Optional[bool] = None
    license: Optional[str] = None
    url: Optional[str] = None
    citation_count: Optional[int] = 0
    keywords: Optional[List[str]] = []
    topics: Optional[List[str]] = []
    metrics: Optional[Dict] = {}
    raw: Optional[Dict] = {}
