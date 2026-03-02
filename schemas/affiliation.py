from typing import Optional
from pydantic import BaseModel, Field


class AffiliationBase(BaseModel):
    author_external_id: str = Field(
        ..., description="External ID of the author (OpenAlex, etc.)"
    )
    research_item_id: int = Field(..., description="ID of the research item")
    organization_id: Optional[int] = Field(None, description="ID of the organization")
    institution_id: Optional[int] = Field(None, description="ID of the institution")
    external_id: Optional[str] = Field(None, description="External ID from source")
    display_name: Optional[str] = Field(None, description="Display name")
    ror: Optional[str] = Field(None, description="ROR ID")
    country_code: Optional[str] = Field(None, description="Country code")
    affiliation_type: Optional[str] = Field(None, description="Type of affiliation")
    role: Optional[str] = Field(None, description="Author role")


class AffiliationCreate(AffiliationBase):
    pass


class AffiliationUpdate(BaseModel):
    author_external_id: Optional[str] = None
    research_item_id: Optional[int] = None
    organization_id: Optional[int] = None
    institution_id: Optional[int] = None
    external_id: Optional[str] = None
    display_name: Optional[str] = None
    ror: Optional[str] = None
    country_code: Optional[str] = None
    affiliation_type: Optional[str] = None
    role: Optional[str] = None


class AffiliationRead(AffiliationBase):
    id: int

    class Config:
        from_attributes = True
