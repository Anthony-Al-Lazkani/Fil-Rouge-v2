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

    # Entity (unified: company, institution, research_lab, university, etc.)
    entity_id: Optional[int] = Field(None, description="Entity ID (FK to Entity table)")
    entity_name: Optional[str] = Field(None, description="Entity name")
    entity_type: Optional[str] = Field(
        None, description="Entity type: company, institution, etc."
    )
    entity_external_id: Optional[str] = Field(
        None, description="External ID (OpenAlex, ROR, SIREN, etc.)"
    )
    entity_ror: Optional[str] = Field(None, description="ROR ID")
    entity_country_code: Optional[str] = Field(None, description="Country code")

    # Legacy fields (deprecated - use entity_* fields instead)
    institution_external_id: Optional[str] = Field(
        None, description="[DEPRECATED] Use entity_external_id"
    )
    institution_name: Optional[str] = Field(
        None, description="[DEPRECATED] Use entity_name"
    )
    institution_ror: Optional[str] = Field(
        None, description="[DEPRECATED] Use entity_ror"
    )
    institution_country_code: Optional[str] = Field(
        None, description="[DEPRECATED] Use entity_country_code"
    )
    institution_type: Optional[str] = Field(
        None, description="[DEPRECATED] Use entity_type"
    )
    organization_id: Optional[int] = Field(
        None, description="[DEPRECATED] Use entity_id"
    )
    organization_name: Optional[str] = Field(
        None, description="[DEPRECATED] Use entity_name"
    )

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
    entity_id: Optional[int] = None
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    entity_external_id: Optional[str] = None
    entity_ror: Optional[str] = None
    entity_country_code: Optional[str] = None
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
