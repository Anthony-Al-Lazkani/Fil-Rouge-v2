from pydantic import BaseModel, Field

class ResearchItemFieldCreate(BaseModel):
    research_item_id: int = Field(..., description="ID de l'article de recherche")
    field_of_study_id: int = Field(..., description="ID du domaine d'étude")
