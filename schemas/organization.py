from typing import Optional
from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    external_id: Optional[str] = Field(
        None,
        description="Identifiant pivot (ID HAL, ROR ou autre) pour éviter les doublons techniques",
    )
    name: str = Field(..., description="Original name of the organization")
    clean_name: Optional[str] = Field(None, description="Cleaned name for analysis")
    type: Optional[str] = Field(
        None, description="Categorization (company, education, facility, archive)"
    )
    country: Optional[str] = Field(None, description="Country")
    city: Optional[str] = Field(None, description="City")


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    external_id: Optional[str] = None
    name: Optional[str] = None
    clean_name: Optional[str] = None
    type: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None


class OrganizationRead(OrganizationBase):
    id: int

    class Config:
        from_attributes = True
