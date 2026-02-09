from sqlmodel import Session, select
from models.affiliation import Affiliation
from schemas.affiliation import AffiliationCreate

class AffiliationService:
    def create(self, session: Session, data: AffiliationCreate):
        """
        Creates a new Affiliation link in the database,
        or returns existing if duplicate by (author_id, research_item_id, organization_id).
        """
        # Check if link already exists
        existing = session.exec(
            select(Affiliation).where(
                Affiliation.author_id == data.author_id,
                Affiliation.research_item_id == data.research_item_id,
                Affiliation.organization_id == data.organization_id
            )
        ).first()
        if existing:
            return existing

        # Create new link
        link = Affiliation(**data.model_dump())
        session.add(link)
        session.commit()
        session.refresh(link)
        return link

    def get_all(self, session: Session, skip: int = 0, limit: int = 100):
        """
        Get all affiliations with pagination.
        """
        return session.exec(
            select(Affiliation).offset(skip).limit(limit)
        ).all()

    def get_by_author(self, session: Session, author_id: int):
        """
        Get all affiliations for a specific author.
        """
        return session.exec(
            select(Affiliation)
            .where(Affiliation.author_id == author_id)
        ).all()

    def get_by_organization(self, session: Session, organization_id: int):
        """
        Get all affiliations for a specific organization.
        """
        return session.exec(
            select(Affiliation)
            .where(Affiliation.organization_id == organization_id)
        ).all()

    def get_by_research_item(self, session: Session, research_item_id: int):
        """
        Get all affiliations for a specific research item.
        """
        return session.exec(
            select(Affiliation)
            .where(Affiliation.research_item_id == research_item_id)
        ).all()

    def get_author_orgs_for_item(self, session: Session, author_id: int, research_item_id: int):
        """
        Get all organizations where an author was affiliated for a specific research item.
        Useful to see if an author had multiple affiliations for one paper.
        """
        return session.exec(
            select(Affiliation).where(
                Affiliation.author_id == author_id,
                Affiliation.research_item_id == research_item_id
            )
        ).all()
