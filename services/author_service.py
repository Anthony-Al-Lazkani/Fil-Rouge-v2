from sqlmodel import Session, select
from models.author import Author
from schemas.author import AuthorCreate


class AuthorService:
    def create(self, session: Session, data: AuthorCreate):
        # check if author already exists by external_id or full_name
        existing = None
        if data.external_id:
            existing = session.exec(
                select(Author).where(Author.external_id == data.external_id)
            ).first()

        if not existing:
            existing = session.exec(
                select(Author).where(Author.full_name == data.full_name)
            ).first()

        if existing:
            return existing

        # create new record
        author = Author(**data.dict())
        session.add(author)
        session.commit()
        session.refresh(author)
        return author

    def get_by_external_id(self, session: Session, external_id: str):
        return session.exec(
            select(Author).where(Author.external_id == external_id)
        ).first()

    def get_by_id(self, session: Session, author_id: int):
        return session.exec(select(Author).where(Author.id == author_id)).first()

    def get_all(self, session: Session):
        """
        Returns all authors in the database.
        """
        return session.exec(select(Author)).all()

    def update(self, session: Session, author_id: int, data: dict):
        author = self.get_by_id(session, author_id)
        if not author:
            return None

        for key, value in data.items():
            if hasattr(author, key):
                setattr(author, key, value)

        session.commit()
        session.refresh(author)
        return author

    def delete(self, session: Session, author_id: int):
        author = self.get_by_id(session, author_id)
        if not author:
            return False

        session.delete(author)
        session.commit()
        return True
