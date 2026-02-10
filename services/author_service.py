from sqlmodel import Session, select
from models.author import Author
from schemas.author import AuthorCreate

class AuthorService:
    def create(self, session: Session, data: AuthorCreate):
        """
        Creates a new Author in the database, or returns existing if duplicate by name.
        """
        # check if source already exists
        existing = session.exec(select(Author).where(Author.full_name == data.full_name)).first()
        if existing:
            return existing

        author = Author(**data.model_dump())
        session.add(author)
        session.commit()
        session.refresh(author)
        return author

    def get_by_name(self, session: Session, full_name: str):
        """
        Get a Source by its name.
        """
        return session.exec(select(Author).where(Author.name == full_name)).first()

    def get_by_external_id(self, session: Session, external_id: str):
        """
        Get an Author by their external_id (ORCID, IdHAL, etc.).
        """
        return session.exec(
            select(Author).where(Author.external_id == external_id)
        ).first()

    def get_all(self, session: Session):
        """
        Get all sources in the database.
        """
        return session.exec(select(Author)).all()
