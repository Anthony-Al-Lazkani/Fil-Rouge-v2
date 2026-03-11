from typing import Optional, List
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class Entity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: Optional[int] = Field(default=None, foreign_key="source.id", index=True)
    external_id: Optional[str] = Field(default=None, index=True, unique=True)
    ror: Optional[str] = Field(default=None, index=True)

    name: str = Field(index=True)
    display_name: Optional[str] = Field(default=None, index=True)
    display_name_acronyms: Optional[List[str]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    display_name_alternatives: Optional[List[str]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )

    entity_type: Optional[str] = Field(default=None, index=True)
    type: Optional[str] = Field(default=None, index=True)

    country: Optional[str] = Field(default=None, index=True)
    country_code: Optional[str] = Field(default=None, index=True)
    city: Optional[str] = Field(default=None)

    homepage_url: Optional[str] = None
    website: Optional[str] = None

    description: Optional[str] = None
    founded_date: Optional[str] = None

    industries: Optional[List[str]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    operating_status: Optional[str] = None
    number_of_employees: Optional[str] = None
    estimated_revenue: Optional[str] = None

    total_funding: Optional[float] = None
    last_funding_amount: Optional[float] = None
    last_funding_date: Optional[str] = None
    number_of_funding_rounds: Optional[int] = None
    number_of_investors: Optional[int] = None

    valuation: Optional[float] = None
    acquisition_count: Optional[int] = None
    ipo: Optional[bool] = None
    acquired: Optional[bool] = None

    founders: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    number_of_founders: Optional[int] = None

    works_count: Optional[int] = Field(default=0)
    cited_by_count: Optional[int] = Field(default=0)

    associated_entities: Optional[List[dict]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    counts_by_year: Optional[List[dict]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )

    is_ai_related: Optional[bool] = None
    ai_focus_percent: Optional[int] = None

    raw: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSON))
