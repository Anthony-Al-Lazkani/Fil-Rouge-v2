from sqlmodel import Session, select
from models.source import Source
from schemas.source import SourceCreate


class SourceService:
    def create(self, session: Session, data: SourceCreate):
        """
        Creates a new Source in the database, or returns existing if duplicate by name.
        """
        # check if source already exists
        existing = session.exec(select(Source).where(Source.name == data.name)).first()
        if existing:
            return existing

        source = Source(**data.dict())
        session.add(source)
        session.commit()
        session.refresh(source)
        return source

    def get_by_name(self, session: Session, name: str):
        """
        Get a Source by its name.
        """
        return session.exec(select(Source).where(Source.name == name)).first()

    def get_all(self, session: Session):
        """
        Get all sources in the database.
        """
        return session.exec(select(Source)).all()
