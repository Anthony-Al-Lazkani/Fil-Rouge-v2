"""
Pour avoir mieux qu'une liste de noms
"""

from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class Author(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Identifiants pivots internationaux (ORCID, OpenAlex ID, HAL ID, etc.)
    external_id: Optional[str] = Field(default=None, index=True, unique=True)
    # unique=True sur les external_id => la base refusera techniquement de créer deux fois le même laboratoire ou le même auteur, même si vous les croisez dans des sources différentes

    full_name: str = Field(index=True)

    # ORCID identifier
    orcid: Optional[str] = Field(default=None, index=True)

    # Roles in publication (corresponding_author, first_author, co_author)
    roles: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))

    # Affiliations as list of dicts with id, name, country, type
    affiliations: Optional[List[Dict]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )

    # Métriques simplifiées pour le profilage
    publication_count: int = Field(default=0)
