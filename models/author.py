'''
Pour avoir mieux qu'une liste de noms
'''

from typing import Optional
from sqlmodel import SQLModel, Field

class Author(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Identifiants pivots internationaux (ORCID, IdHAL, etc.)
    external_id: Optional[str] = Field(default=None, index=True, unique=True)
    # unique=True sur les external_id => la base refusera techniquement de créer deux fois le même laboratoire ou le même auteur, même si vous les croisez dans des sources différentes
    
    full_name: str = Field(index=True)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    # Métriques simplifiées pour le profilage
    publication_count: int = Field(default=0)