# services/organization_service.py
from sqlmodel import Session, select
from models.organization import Organization
from schemas.organization import OrganizationCreate

class OrganizationService:
    def create(self, session: Session, data: OrganizationCreate):
        """
        Creates a new Organization in the database,
        or returns existing if duplicate by name.
        """
        # Check if organization already exists by name
        if data.external_id:
            existing = session.exec(
                select(Organization).where(Organization.name == data.name)
            ).first()
            if existing:
                return existing

        # Create new organization
        org = Organization(**data.model_dump())
        session.add(org)
        session.commit()
        session.refresh(org)
        return org

    def get_all(self, session: Session):
        """
        Get all organizations (no pagination).
        """
        return session.exec(select(Organization)).all()

    def get_by_external_id(self, session: Session, external_id: str):
        """
        Get an organization by its external ID (ROR, GRID, etc.).
        """
        return session.exec(select(Organization).where(Organization.external_id == external_id)).first()

    def get_by_name(self, session: Session, name: str):
        """
        Get an organization by its exact name.
        """
        return session.exec(select(Organization).where(Organization.name == name)).first()

    def get_by_clean_name(self, session: Session, clean_name: str):
        """
        Get an organization by its cleaned/normalized name.
        """
        return session.exec(select(Organization).where(Organization.clean_name == clean_name)).first()

    def get_by_type(self, session: Session, org_type: str):
        """
        Get all organizations of a specific type (education, company, etc.).
        """
        return session.exec(select(Organization).where(Organization.type == org_type)).all()

    def get_by_country(self, session: Session, country: str):
        """
        Get all organizations in a specific country.
        """
        return session.exec(select(Organization).where(Organization.country == country)).all()

    def search_by_name(self, session: Session, search_term: str):
        """
        Search organizations by partial name match (case-insensitive).
        """
        return session.exec(select(Organization).where(Organization.name.ilike(f"%{search_term}%"))).all()
