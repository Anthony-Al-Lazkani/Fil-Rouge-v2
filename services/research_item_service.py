from sqlmodel import Session, select
from models.research_item import ResearchItem
from schemas.research_item import ResearchItemCreate

class ResearchItemService:
    def create(self, session: Session, data: ResearchItemCreate):
        # check if item already exists
        existing = session.exec(
            select(ResearchItem).where(
                (ResearchItem.source_id == data.source_id) &
                (ResearchItem.external_id == data.external_id)
            )
        ).first()
        if existing:
            return existing

        # create new record
        item = ResearchItem(**data.dict())
        session.add(item)
        session.commit()
        session.refresh(item)
        return item

    def get_by_external_id(self, session: Session, source_id: int, external_id: str):
        return session.exec(
            select(ResearchItem).where(
                (ResearchItem.source_id == source_id) &
                (ResearchItem.external_id == external_id)
            )
        ).first()

    def get_all(self, session: Session):
        """
        Returns all research items in the database.
        """
        return session.exec(select(ResearchItem)).all()
