"""
Représentation unique des chercheurs et contributeurs.

Features:
- Identification unique via external_id (OpenAlex, HAL) et ORCID.
- Centralisation des métriques de publication.
- Suppression des données d'affiliation redondantes (gérées par la table Affiliation).
"""

from typing import Optional
from sqlmodel import SQLModel, Field

class Author(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Identifiants pivots
    external_id: Optional[str] = Field(default=None, index=True, unique=True)
    orcid: Optional[str] = Field(default=None, index=True)

    # Identité
    full_name: str = Field(index=True)

    # Métriques simplifiées pour le profilage (évite des COUNT lourds en SQL)
    publication_count: int = Field(default=0)