from typing import Optional, List, Union
from pydantic import BaseModel, Field


class EntityBase(BaseModel):
    source_id: Optional[int] = Field(None, description="Source ID")
    external_id: Optional[str] = Field(None, description="External ID")
    ror: Optional[str] = Field(None, description="ROR ID")

    name: str = Field(..., description="Name")
    display_name: Optional[str] = Field(None, description="Display name")
    display_name_acronyms: Optional[List[str]] = Field(
        default_factory=list, description="Acronyms"
    )
    display_name_alternatives: Optional[List[str]] = Field(
        default_factory=list, description="Alternative names"
    )

    entity_type: Optional[str] = Field(
        None, description="Entity type: company, institution, research_lab, university"
    )
    type: Optional[str] = Field(
        None, description="Type (company_type, institution_type)"
    )

    country: Optional[str] = Field(None, description="Country")
    country_code: Optional[str] = Field(None, description="Country code")
    city: Optional[str] = Field(None, description="City")

    homepage_url: Optional[str] = Field(None, description="Homepage URL")
    website: Optional[str] = Field(None, description="Website")

    description: Optional[str] = Field(None, description="Description")
    founded_date: Optional[str] = Field(None, description="Founded date")

    industries: Optional[List[str]] = Field(
        default_factory=list, description="Industries"
    )
    operating_status: Optional[str] = Field(None, description="Operating status")
    number_of_employees: Optional[str] = Field(None, description="Number of employees")
    estimated_revenue: Optional[str] = Field(None, description="Estimated revenue")

    total_funding: Optional[Union[float, int]] = Field(
        None, description="Total funding"
    )
    last_funding_amount: Optional[Union[float, int]] = Field(
        None, description="Last funding amount"
    )
    last_funding_date: Optional[str] = Field(None, description="Last funding date")
    number_of_funding_rounds: Optional[Union[int, str]] = Field(
        None, description="Funding rounds"
    )
    number_of_investors: Optional[Union[int, str]] = Field(
        None, description="Number of investors"
    )

    valuation: Optional[Union[float, int]] = Field(None, description="Valuation")
    acquisition_count: Optional[Union[int, float, str]] = Field(
        None, description="Acquisitions"
    )
    ipo: Optional[bool] = Field(None, description="IPO")
    acquired: Optional[bool] = Field(None, description="Acquired")

    founders: Optional[List[str]] = Field(default_factory=list, description="Founders")
    number_of_founders: Optional[int] = Field(None, description="Number of founders")

    works_count: Optional[int] = Field(default=0, description="Works count")
    cited_by_count: Optional[int] = Field(default=0, description="Cited by count")

    associated_entities: Optional[List[dict]] = Field(
        default_factory=list, description="Associated entities"
    )
    counts_by_year: Optional[List[dict]] = Field(
        default_factory=list, description="Counts by year"
    )

    is_ai_related: Optional[bool] = Field(None, description="AI related")
    ai_focus_percent: Optional[Union[int, str]] = Field(None, description="AI focus %")

    raw: Optional[dict] = Field(default_factory=dict, description="Raw data")


class EntityCreate(EntityBase):
    pass


class EntityUpdate(BaseModel):
    source_id: Optional[int] = None
    external_id: Optional[str] = None
    ror: Optional[str] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    display_name_acronyms: Optional[List[str]] = None
    display_name_alternatives: Optional[List[str]] = None
    entity_type: Optional[str] = None
    type: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    homepage_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    founded_date: Optional[str] = None
    industries: Optional[List[str]] = None
    operating_status: Optional[str] = None
    number_of_employees: Optional[str] = None
    estimated_revenue: Optional[str] = None
    total_funding: Optional[Union[float, int]] = None
    last_funding_amount: Optional[Union[float, int]] = None
    last_funding_date: Optional[str] = None
    number_of_funding_rounds: Optional[Union[int, str]] = None
    number_of_investors: Optional[Union[int, str]] = None
    valuation: Optional[Union[float, int]] = None
    acquisition_count: Optional[Union[int, float, str]] = None
    ipo: Optional[bool] = None
    acquired: Optional[bool] = None
    founders: Optional[List[str]] = None
    number_of_founders: Optional[int] = None
    works_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    associated_entities: Optional[List[dict]] = None
    counts_by_year: Optional[List[dict]] = None
    is_ai_related: Optional[bool] = None
    ai_focus_percent: Optional[Union[int, str]] = None
    raw: Optional[dict] = None


class EntityRead(EntityBase):
    id: int

    class Config:
        from_attributes = True
