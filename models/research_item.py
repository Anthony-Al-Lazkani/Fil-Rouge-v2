'définit la structure de la table ResearchItem (réceptacle des crawler académiques)'
'Attention: doi : unique=true'

from typing import Optional, Dict, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON, Text
from models.authorResearchItem import AuthorResearchItem

if TYPE_CHECKING:
    from models.author import Author

class ResearchItem(SQLModel, table=True):
    __tablename__ = "research_item"
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int  # FK to Source table
    external_id: str  # ID from the source (OpenAlex, arXiv, etc.)
    doi: Optional[str] = Field(default=None, unique=True, index=True)
    title: Optional[str]
    year: Optional[int]
    type: Optional[str]  # paper, preprint, article
    abstract: Optional[str] = Field(default=None, sa_column=Column(Text))
    is_retracted: bool = False
    is_open_access: Optional[bool]
    references: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))  # Liste de DOIs ou IDs
    metrics: Optional[Dict] = Field(default_factory=dict, sa_column=Column(JSON))
    raw: Optional[Dict] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    authors: List["AuthorResearchItem"] = Relationship(back_populates="research_item")
