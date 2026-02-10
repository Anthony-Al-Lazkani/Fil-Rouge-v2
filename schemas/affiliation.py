from typing import Optional
from pydantic import BaseModel, Field


class AffiliationBase(BaseModel):
    author_id: int = Field(..., description="ID of the author")
    organization_id: Optional[int] = Field(
        None, description="ID of the organization (nullable)"
    )
    research_item_id: int = Field(..., description="ID of the research item")


class AffiliationCreate(AffiliationBase):
    pass


class AffiliationUpdate(BaseModel):
    author_id: Optional[int] = None
    organization_id: Optional[int] = None
    research_item_id: Optional[int] = None


class AffiliationRead(AffiliationBase):
    id: int

    class Config:
        from_attributes = True
