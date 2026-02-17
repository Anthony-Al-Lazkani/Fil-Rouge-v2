from typing import Optional, List, Union
from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    source: Optional[str] = Field(None, description="Source of data")
    external_id: Optional[str] = Field(None, description="External ID")
    name: str = Field(..., description="Original name")
    clean_name: Optional[str] = Field(None, description="Cleaned name")
    type: Optional[str] = Field(None, description="Type")
    country: Optional[str] = Field(None, description="Country")
    city: Optional[str] = Field(None, description="City")
    description: Optional[str] = Field(None, description="Description")
    founded_date: Optional[str] = Field(None, description="Founded date")
    industries: Optional[List[str]] = Field(
        default_factory=list, description="Industries"
    )
    operating_status: Optional[str] = Field(None, description="Operating status")
    number_of_employees: Optional[str] = Field(None, description="Number of employees")
    estimated_revenue: Optional[str] = Field(None, description="Estimated revenue")
    website: Optional[str] = Field(None, description="Website")
    total_funding: Optional[Union[float, int]] = Field(
        None, description="Total funding"
    )
    last_funding_amount: Optional[Union[float, int]] = Field(
        None, description="Last funding"
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
    is_ai_related: Optional[bool] = Field(None, description="AI related")
    ai_focus_percent: Optional[Union[int, str]] = Field(None, description="AI focus %")


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    source: Optional[str] = None
    external_id: Optional[str] = None
    name: Optional[str] = None
    clean_name: Optional[str] = None
    type: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    founded_date: Optional[str] = None
    industries: Optional[List[str]] = None
    operating_status: Optional[str] = None
    number_of_employees: Optional[str] = None
    estimated_revenue: Optional[str] = None
    website: Optional[str] = None
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
    is_ai_related: Optional[bool] = None
    ai_focus_percent: Optional[Union[int, str]] = None


class OrganizationRead(OrganizationBase):
    id: int

    class Config:
        from_attributes = True
