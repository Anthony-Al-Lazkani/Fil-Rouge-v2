# services/field_of_study_service.py
from sqlmodel import Session, select
from models.fieldsOfStudy import FieldOfStudy
from schemas.fieldsOfStudy import FieldOfStudyCreate

class FieldOfStudyService:
    def create(self, session: Session, data: FieldOfStudyCreate):
        """
        Creates a new FieldOfStudy in the database,
        or returns existing if duplicate by field name.
        """
        # Check if field already exists
        existing = session.exec(select(FieldOfStudy).where(FieldOfStudy.field == data.field)).first()
        if existing:
            return existing

        # Create new field
        field = FieldOfStudy(**data.model_dump())
        session.add(field)
        session.commit()
        session.refresh(field)
        return field

    def get_all(self, session: Session):
        """
        Get all fields of study with pagination.
        """
        return session.exec(select(FieldOfStudy)).all()

    def get_by_field(self, session: Session, field: str):
        """
        Get a field of study by its English name.
        """
        return session.exec(select(FieldOfStudy).where(FieldOfStudy.field == field)).first()

    def get_by_domaine(self, session: Session, domaine: str):
        """
        Get a field of study by its French name.
        """
        return session.exec(select(FieldOfStudy).where(FieldOfStudy.domaine == domaine)).first()

    def get_by_wikidata_id(self, session: Session, wikidata_id: str):
        """
        Get a field of study by its Wikidata ID.
        """
        return session.exec(select(FieldOfStudy).where(FieldOfStudy.wikidata_id == wikidata_id)).first()

    def get_by_arxiv_category(self, session: Session, arxiv_category: str):
        """
        Get a field of study by its ArXiv category.
        """
        return session.exec(select(FieldOfStudy).where(FieldOfStudy.arxiv_category == arxiv_category)).first()
