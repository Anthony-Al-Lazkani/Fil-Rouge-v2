from sqlmodel import Session, select
from models.source import Source
from schemas.author import AuthorCreate

class AuthorService:
    def create(self, session: Session, data: AuthorCreate):
        """
        Creates a new Author in the database, or returns existing if duplicate by name.
        """
        # check if source already exists
        existing = session.exec(select(Author).where(Author.name == data.name)).first()
        if existing:
            return existing

        author = Author(**data.dict())
        session.add(author)
        session.commit()
        session.refresh(author)
        return author

    def get_by_name(self, session: Session, name: str):
        """
        Get a Source by its name.
        """
        return session.exec(select(Author).where(Author.name == name)).first()

    def get_all(self, session: Session):
        """
        Get all sources in the database.
        """
        return session.exec(select(Author)).all()
