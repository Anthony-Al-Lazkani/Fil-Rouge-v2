from typing import Optional
from pydantic import BaseModel, Field

class OrganizationCreate(BaseModel):
    external_id: Optional[str] = Field(None, description="ID externe (ROR, IdHAL, etc.)")
    name: str
    clean_name: Optional[str] = Field(None, description="Nom nettoyé pour l'analyse")
    type: Optional[str] = Field(None, description="Type: company, education, facility, archive")
    country: Optional[str] = Field(None, description="Pays de l'organisation")
    city: Optional[str] = Field(None, description="Ville de l'organisation")
