'''
Cette table va enregistrer chaque relation unique. Elle répond à la question : "Qui travaillait où pour quel article ?"
'''
from typing import Optional
from sqlmodel import SQLModel, Field

class Affiliation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Les trois piliers de la relation
    author_id: int = Field(foreign_key="author.id", index=True)
    organization_id: Optional[int] = Field(default=None, foreign_key="organization.id", nullable=True)
    research_item_id: int = Field(foreign_key="researchitem.id", index=True)