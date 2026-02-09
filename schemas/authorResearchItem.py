from typing import Optional
from pydantic import BaseModel, Field

class AuthorResearchItemCreate(BaseModel):
    author_id: int
    research_item_id: int
    author_order: Optional[int] = Field(None, description="Ordre de l'auteur dans la liste (0 = premier auteur)")
