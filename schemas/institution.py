from typing import Optional, List
from pydantic import BaseModel, Field


class InstitutionBase(BaseModel):
    source: Optional[str] = Field("openalex", description="Source of data")
    external_id: Optional[str] = Field(None, description="External ID from OpenAlex")
    ror: Optional[str] = Field(None, description="ROR ID")
    display_name: str = Field(..., description="Display name")
    display_name_acronyms: Optional[List[str]] = Field(
        default_factory=list, description="Acronyms"
    )
    display_name_alternatives: Optional[List[str]] = Field(
        default_factory=list, description="Alternative names"
    )
    country_code: Optional[str] = Field(None, description="Country code")
    type: Optional[str] = Field(None, description="Institution type")
    homepage_url: Optional[str] = Field(None, description="Homepage URL")
    works_count: Optional[int] = Field(0, description="Works count")
    cited_by_count: Optional[int] = Field(0, description="Cited by count")
    associated_institutions: Optional[List[dict]] = Field(
        default_factory=list, description="Associated institutions"
    )
    counts_by_year: Optional[List[dict]] = Field(
        default_factory=list, description="Counts by year"
    )


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionUpdate(BaseModel):
    source: Optional[str] = None
    external_id: Optional[str] = None
    ror: Optional[str] = None
    display_name: Optional[str] = None
    display_name_acronyms: Optional[List[str]] = None
    display_name_alternatives: Optional[List[str]] = None
    country_code: Optional[str] = None
    type: Optional[str] = None
    homepage_url: Optional[str] = None
    works_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    associated_institutions: Optional[List[dict]] = None
    counts_by_year: Optional[List[dict]] = None


class InstitutionRead(InstitutionBase):
    id: int

    class Config:
        from_attributes = True
