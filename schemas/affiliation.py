from typing import Optional, Dict
from pydantic import BaseModel, Field


class AffiliationBase(BaseModel):
    # Research Item
    research_item_id: int = Field(..., description="Internal ID of the research item")
    research_item_external_id: str = Field(
        ..., description="External ID of the research item"
    )
    research_item_doi: Optional[str] = Field(
        None, description="DOI of the research item"
    )
    research_item_title: Optional[str] = Field(
        None, description="Title of the research item"
    )
    research_item_year: Optional[int] = Field(None, description="Publication year")
    research_item_source: Optional[str] = Field(
        None, description="Source (openalex, arxiv, etc.)"
    )

    # Author
    author_external_id: str = Field(..., description="External ID of the author")
    author_full_name: Optional[str] = Field(None, description="Author full name")
    author_orcid: Optional[str] = Field(None, description="Author ORCID")

    # Institution
    institution_external_id: Optional[str] = Field(
        None, description="External ID of institution (OpenAlex, ROR)"
    )
    institution_name: Optional[str] = Field(None, description="Institution name")
    institution_ror: Optional[str] = Field(None, description="ROR ID")
    institution_country_code: Optional[str] = Field(None, description="Country code")
    institution_type: Optional[str] = Field(None, description="Institution type")

    # Organization (alternative)
    organization_id: Optional[int] = Field(None, description="Organization ID")
    organization_name: Optional[str] = Field(None, description="Organization name")

    # Role
    role: Optional[str] = Field(None, description="Author role in publication")
    raw_affiliation_data: Optional[Dict] = Field(
        None, description="Raw affiliation data"
    )


class AffiliationCreate(AffiliationBase):
    pass


class AffiliationUpdate(BaseModel):
    research_item_id: Optional[int] = None
    research_item_external_id: Optional[str] = None
    research_item_doi: Optional[str] = None
    research_item_title: Optional[str] = None
    research_item_year: Optional[int] = None
    research_item_source: Optional[str] = None
    author_external_id: Optional[str] = None
    author_full_name: Optional[str] = None
    author_orcid: Optional[str] = None
    institution_external_id: Optional[str] = None
    institution_name: Optional[str] = None
    institution_ror: Optional[str] = None
    institution_country_code: Optional[str] = None
    institution_type: Optional[str] = None
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    role: Optional[str] = None
    raw_affiliation_data: Optional[Dict] = None


class AffiliationRead(AffiliationBase):
    id: int

    class Config:
        from_attributes = True
