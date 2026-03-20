"""
Exportation des modèles de données épurés.

Features:
- Centralise les classes SQLModel pour l'initialisation de la BDD.
- Expose les entités : Source, ResearchItem, Entity, Author et Affiliation.
- Facilite les imports circulaires lors des jointures.
"""

from .source import Source
from .research_item import ResearchItem
from .entity import Entity
from .author import Author
from .affiliation import Affiliation