from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON
from models.source import Source


class Institution(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: Optional[int] = Field(default=None, foreign_key="source.id", index=True)
    external_id: Optional[str] = Field(default=None, index=True, unique=True)
    ror: Optional[str] = Field(default=None, index=True)

    display_name: str = Field(index=True)
    display_name_acronyms: Optional[List[str]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    display_name_alternatives: Optional[List[str]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )

    country_code: Optional[str] = Field(default=None, index=True)
    type: Optional[str] = Field(default=None, index=True)
    homepage_url: Optional[str] = None

    works_count: Optional[int] = Field(default=0)
    cited_by_count: Optional[int] = Field(default=0)

    associated_institutions: Optional[List[dict]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    counts_by_year: Optional[List[dict]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )

    raw: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSON))
