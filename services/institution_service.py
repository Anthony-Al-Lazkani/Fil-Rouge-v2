from typing import Optional, List
from sqlmodel import Session, select
from models.institution import Institution
from schemas.institution import InstitutionCreate, InstitutionUpdate


class InstitutionService:
    def create(self, session: Session, data: InstitutionCreate):
        existing = None
        if data.external_id:
            existing = session.exec(
                select(Institution).where(Institution.external_id == data.external_id)
            ).first()

        if not existing and data.ror:
            existing = session.exec(
                select(Institution).where(Institution.ror == data.ror)
            ).first()

        if existing:
            return existing

        inst = Institution(**data.dict(exclude_unset=True))
        session.add(inst)
        session.commit()
        session.refresh(inst)
        return inst

    def create_many(self, session: Session, data_list: List[InstitutionCreate]) -> int:
        count = 0
        for data in data_list:
            self.create(session, data)
            count += 1
        return count

    def get_by_external_id(self, session: Session, external_id: str):
        return session.exec(
            select(Institution).where(Institution.external_id == external_id)
        ).first()

    def get_by_ror(self, session: Session, ror: str):
        return session.exec(select(Institution).where(Institution.ror == ror)).first()

    def get_by_id(self, session: Session, inst_id: int):
        return session.exec(
            select(Institution).where(Institution.id == inst_id)
        ).first()

    def get_all(self, session: Session, limit: Optional[int] = None, offset: int = 0):
        query = select(Institution)
        if limit:
            query = query.offset(offset).limit(limit)
        return session.exec(query).all()

    def get_by_country(self, session: Session, country_code: str):
        return session.exec(
            select(Institution).where(Institution.country_code == country_code)
        ).all()

    def get_by_type(self, session: Session, inst_type: str):
        return session.exec(
            select(Institution).where(Institution.type == inst_type)
        ).all()

    def count(self, session: Session) -> int:
        return session.exec(select(Institution)).all().__len__()

    def update(self, session: Session, inst_id: int, data: dict):
        inst = self.get_by_id(session, inst_id)
        if not inst:
            return None

        for key, value in data.items():
            if hasattr(inst, key):
                setattr(inst, key, value)

        session.commit()
        session.refresh(inst)
        return inst

    def delete(self, session: Session, inst_id: int):
        inst = self.get_by_id(session, inst_id)
        if not inst:
            return False

        session.delete(inst)
        session.commit()
        return True

    def delete_all(self, session: Session):
        session.exec(select(Institution))
        session.query(Institution).delete()
        session.commit()
