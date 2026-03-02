from typing import Optional, List
from sqlmodel import Session, select
from models.affiliation import Affiliation
from schemas.affiliation import AffiliationCreate, AffiliationUpdate


class AffiliationService:
    def create(self, session: Session, data: AffiliationCreate):
        existing = session.exec(
            select(Affiliation).where(
                Affiliation.author_id == data.author_id,
                Affiliation.research_item_id == data.research_item_id,
                Affiliation.external_id == data.external_id,
            )
        ).first()

        if existing:
            return existing

        aff = Affiliation(**data.dict(exclude_unset=True))
        session.add(aff)
        session.commit()
        session.refresh(aff)
        return aff

    def create_many(self, session: Session, data_list: List[AffiliationCreate]) -> int:
        count = 0
        for data in data_list:
            self.create(session, data)
            count += 1
        return count

    def get_by_id(self, session: Session, aff_id: int):
        return session.exec(select(Affiliation).where(Affiliation.id == aff_id)).first()

    def get_by_author(self, session: Session, author_id: int):
        return session.exec(
            select(Affiliation).where(Affiliation.author_id == author_id)
        ).all()

    def get_by_research_item(self, session: Session, research_item_id: int):
        return session.exec(
            select(Affiliation).where(Affiliation.research_item_id == research_item_id)
        ).all()

    def get_by_organization(self, session: Session, organization_id: int):
        return session.exec(
            select(Affiliation).where(Affiliation.organization_id == organization_id)
        ).all()

    def get_by_institution(self, session: Session, institution_id: int):
        return session.exec(
            select(Affiliation).where(Affiliation.institution_id == institution_id)
        ).all()

    def get_by_ror(self, session: Session, ror: str):
        return session.exec(select(Affiliation).where(Affiliation.ror == ror)).all()

    def count(self, session: Session) -> int:
        return session.exec(select(Affiliation)).all().__len__()

    def delete_all(self, session: Session):
        session.exec(select(Affiliation))
        session.query(Affiliation).delete()
        session.commit()
