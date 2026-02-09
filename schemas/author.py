from typing import Optional
from pydantic import BaseModel, Field

class AuthorCreate(BaseModel):
    external_id: Optional[str] = Field(None, description="ID externe (ORCID, IdHAL, etc.)")
    full_name: str
    country: Optional[str] = Field(None, description="Pays de l'auteur")
    publication_count: int = Field(default=0)
