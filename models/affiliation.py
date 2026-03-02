"""
Cette table va enregistrer chaque relation unique. Elle répond à la question : "Qui travaillait où pour quel article ?"
"""

from typing import Optional
from sqlmodel import SQLModel, Field


class Affiliation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Use external_id for author (OpenAlex ID, etc.) instead of internal author_id
    author_external_id: str = Field(index=True)
    research_item_id: int = Field(foreign_key="researchitem.id", index=True)

    # Peut être soit organization soit institution (XOR - un des deux doit être non-null)
    organization_id: Optional[int] = Field(
        default=None, foreign_key="organization.id", nullable=True, index=True
    )
    institution_id: Optional[int] = Field(
        default=None, foreign_key="institution.id", nullable=True, index=True
    )

    # Info sur l'affiliation (pour référence au cas où l'org/institution n'existe pas dans notre DB)
    external_id: Optional[str] = Field(
        default=None, index=True
    )  # OpenAlex ID, ROR, etc.
    display_name: Optional[str] = None
    ror: Optional[str] = Field(default=None, index=True)
    country_code: Optional[str] = None
    affiliation_type: Optional[str] = None  # education, company, etc.

    # Rôle de l'auteur dans cette publication
    role: Optional[str] = None  # first_author, corresponding_author, co_author
