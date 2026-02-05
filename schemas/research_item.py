# schemas/research_item.py
from typing import Optional, Dict
from pydantic import BaseModel

class ResearchItemCreate(BaseModel):
    source_id: int
    external_id: str
    doi: Optional[str] = None
    type: str  # "article", "company", etc.
    title: Optional[str]
    year: Optional[int]
    is_retracted: Optional[bool] = False
    is_open_access: Optional[bool] = None
    metrics: Optional[Dict] = {}
    raw: Optional[Dict] = {}
