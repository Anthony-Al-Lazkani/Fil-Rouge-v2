# services/research_item_field_service.py
from sqlmodel import Session, select
from models.researchItemField import ResearchItemField
from schemas.researchItemField import ResearchItemFieldCreate


class ResearchItemFieldService:
    def create(self, session: Session, data: ResearchItemFieldCreate):
        """
        Creates a new ResearchItemField link in the database,
        or returns existing if duplicate.
        """
        # Check if link already exists
        existing = session.exec(
            select(ResearchItemField).where(
                ResearchItemField.research_item_id == data.research_item_id,
                ResearchItemField.field_of_study_id == data.field_of_study_id
            )
        ).first()
        if existing:
            return existing

        # Create new link
        link = ResearchItemField(**data.model_dump())
        session.add(link)
        session.commit()
        session.refresh(link)
        return link

    def get_all(self, session: Session):
        """
        Get all research item field links (no pagination).
        """
        return session.exec(select(ResearchItemField)).all()

    def get_fields_by_research_item(self, session: Session, research_item_id: int):
        """
        Get all fields of study for a specific research item.
        """
        return session.exec(select(ResearchItemField).where(ResearchItemField.research_item_id == research_item_id)).all()

    def get_research_items_by_field(self, session: Session, field_of_study_id: int):
        """
        Get all research items for a specific field of study.
        """
        return session.exec(select(ResearchItemField).where(ResearchItemField.field_of_study_id == field_of_study_id)).all()

    def delete_link(self, session: Session, research_item_id: int, field_of_study_id: int):
        """
        Delete a specific research item <-> field link.
        """
        link = session.exec(
            select(ResearchItemField).where(
                ResearchItemField.research_item_id == research_item_id,
                ResearchItemField.field_of_study_id == field_of_study_id
            )
        ).first()

        if link:
            session.delete(link)
            session.commit()
            return True
        return False

    def delete_all_fields_for_item(self, session: Session, research_item_id: int):
        """
        Delete all field links for a specific research item.
        """
        links = session.exec(
            select(ResearchItemField).where(
                ResearchItemField.research_item_id == research_item_id
            )
        ).all()

        for link in links:
            session.delete(link)
        session.commit()
        return len(links)
