from typing import Optional
from pydantic import BaseModel, Field


class AuthorBase(BaseModel):
    external_id: Optional[str] = Field(
        None, description="Identifiants pivots internationaux (ORCID, IdHAL, etc.)"
    )
    full_name: str = Field(..., description="Full name of the author")
    publication_count: int = Field(0, description="Number of publications")


class AuthorCreate(AuthorBase):
    pass


class AuthorUpdate(BaseModel):
    external_id: Optional[str] = None
    full_name: Optional[str] = None
    publication_count: Optional[int] = None


class AuthorRead(AuthorBase):
    id: int

    class Config:
        from_attributes = True
