from typing import Optional
from pydantic import BaseModel, Field

class FieldOfStudyCreate(BaseModel):
    domaine: Optional[str] = Field(None, description="Nom du domaine en français")
    field: str = Field(..., description="Nom du domaine en anglais")
    wikidata_id: Optional[str] = Field(None, description="Identifiant Wikidata")
    arxiv_category: Optional[str] = Field(None, description="Catégorie ArXiv (ex: cs.AI)")
