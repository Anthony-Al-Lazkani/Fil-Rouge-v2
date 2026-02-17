from typing import Optional, List
from sqlmodel import Session, select
from models.organization import Organization
from schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationService:
    def create(self, session: Session, data: OrganizationCreate):
        existing = None
        if data.external_id:
            existing = session.exec(
                select(Organization).where(Organization.external_id == data.external_id)
            ).first()

        if not existing:
            existing = session.exec(
                select(Organization).where(Organization.name == data.name)
            ).first()

        if existing:
            return existing

        org = Organization(**data.dict(exclude_unset=True))
        session.add(org)
        session.commit()
        session.refresh(org)
        return org

    def create_many(self, session: Session, data_list: List[OrganizationCreate]) -> int:
        count = 0
        for data in data_list:
            self.create(session, data)
            count += 1
        return count

    def get_by_external_id(self, session: Session, external_id: str):
        return session.exec(
            select(Organization).where(Organization.external_id == external_id)
        ).first()

    def get_by_name(self, session: Session, name: str):
        return session.exec(
            select(Organization).where(Organization.name == name)
        ).first()

    def get_by_id(self, session: Session, org_id: int):
        return session.exec(
            select(Organization).where(Organization.id == org_id)
        ).first()

    def get_all(self, session: Session, limit: Optional[int] = None, offset: int = 0):
        query = select(Organization)
        if limit:
            query = query.offset(offset).limit(limit)
        return session.exec(query).all()

    def get_by_source(self, session: Session, source: str):
        return session.exec(
            select(Organization).where(Organization.source == source)
        ).all()

    def get_companies_with_founders(self, session: Session):
        return session.exec(
            select(Organization).where(Organization.founders != None)  # type: ignore
        ).all()

    def get_ai_companies(self, session: Session):
        return session.exec(
            select(Organization).where(Organization.is_ai_related == True)
        ).all()

    def count(self, session: Session) -> int:
        return session.exec(select(Organization)).all().__len__()

    def update(self, session: Session, org_id: int, data: dict):
        org = self.get_by_id(session, org_id)
        if not org:
            return None

        for key, value in data.items():
            if hasattr(org, key):
                setattr(org, key, value)

        session.commit()
        session.refresh(org)
        return org

    def delete(self, session: Session, org_id: int):
        org = self.get_by_id(session, org_id)
        if not org:
            return False

        session.delete(org)
        session.commit()
        return True

    def delete_all(self, session: Session):
        session.exec(select(Organization))
        session.query(Organization).delete()
        session.commit()
