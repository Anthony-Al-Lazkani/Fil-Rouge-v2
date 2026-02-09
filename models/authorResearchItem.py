'''
Cette table de jointure va enregistrer chaque relation entre un auteur et un article. Permettra de répondre aux questions "Qui a collaboré avec qui?"
et "qui a écrit quel article?"
'''
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

if TYPE_CHECKING:
    from author import Author
    from research_item import ResearchItem

class AuthorResearchItem(SQLModel, table=True):
    __tablename__ = "author_research_item"

    # Clés étrangères
    author_id: int = Field(foreign_key="author.id", primary_key=True, index=True)
    research_item_id: int = Field(foreign_key="research_item.id", primary_key=True, index=True)

    # Métadonnée optionnelle
    author_order: Optional[int] = Field(default=None,description="Ordre de l'auteur dans la liste des auteurs (0 = premier auteur).")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relations (pour faciliter les requêtes avec SQLModel)
    author: "Author" = Relationship(back_populates="articles")
    research_item: "ResearchItem" = Relationship(back_populates="authors")