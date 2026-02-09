# services/author_research_item_service.py
from sqlmodel import Session, select
from models.authorResearchItem import AuthorResearchItem
from schemas.authorResearchItem import AuthorResearchItemCreate

class AuthorResearchItemService:
    def create(self, session: Session, data: AuthorResearchItemCreate):
        """
        Creates a new AuthorResearchItem link in the database,
        or returns existing if duplicate by (author_id, research_item_id).
        """
        # Check if link already exists
        existing = session.exec(
            select(AuthorResearchItem).where(
                AuthorResearchItem.author_id == data.author_id,
                AuthorResearchItem.research_item_id == data.research_item_id
            )
        ).first()
        if existing:
            return existing

        # Create new link
        link = AuthorResearchItem(**data.model_dump())
        session.add(link)
        session.commit()
        session.refresh(link)
        return link

    def get_research_items_by_author(self, session: Session, author_id: int):
        """
        Get all research items linked to a specific author.
        """
        return session.exec(
            select(AuthorResearchItem)
            .where(AuthorResearchItem.author_id == author_id)
        ).all()

    def get_authors_by_research_item(self, session: Session, research_item_id: int):
        """
        Get all authors linked to a specific research item.
        """
        return session.exec(
            select(AuthorResearchItem)
            .where(AuthorResearchItem.research_item_id == research_item_id)
        ).all()

    def get_all(self, session: Session, skip: int = 0, limit: int = 100):
        """
        Get all author-research_item links with pagination.
        """
        return session.exec(
            select(AuthorResearchItem).offset(skip).limit(limit)
        ).all()