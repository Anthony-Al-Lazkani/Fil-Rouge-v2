from typing import Optional, List
from sqlmodel import Session, select
from models.entity import Entity
from schemas.entity import EntityCreate, EntityUpdate


class EntityService:
    def create(self, session: Session, data: EntityCreate):
        existing = None
        if data.external_id:
            existing = session.exec(
                select(Entity).where(Entity.external_id == data.external_id)
            ).first()

        if not existing and data.ror:
            existing = session.exec(
                select(Entity).where(Entity.ror == data.ror)
            ).first()

        if not existing:
            existing = session.exec(
                select(Entity).where(Entity.name == data.name)
            ).first()

        if existing:
            return existing

        entity = Entity(**data.dict(exclude_unset=True))
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return entity

    def create_many(self, session: Session, data_list: List[EntityCreate]) -> int:
        count = 0
        for data in data_list:
            self.create(session, data)
            count += 1
        return count

    def get_by_external_id(self, session: Session, external_id: str):
        return session.exec(
            select(Entity).where(Entity.external_id == external_id)
        ).first()

    def get_by_ror(self, session: Session, ror: str):
        return session.exec(select(Entity).where(Entity.ror == ror)).first()

    def get_by_name(self, session: Session, name: str):
        return session.exec(select(Entity).where(Entity.name == name)).first()

    def get_by_id(self, session: Session, entity_id: int):
        return session.exec(select(Entity).where(Entity.id == entity_id)).first()

    def get_all(self, session: Session, limit: Optional[int] = None, offset: int = 0):
        query = select(Entity)
        if limit:
            query = query.offset(offset).limit(limit)
        return session.exec(query).all()

    def get_by_source(self, session: Session, source: str):
        return session.exec(select(Entity).where(Entity.source_id == source)).all()

    def get_by_entity_type(self, session: Session, entity_type: str):
        return session.exec(
            select(Entity).where(Entity.entity_type == entity_type)
        ).all()

    def get_companies(self, session: Session):
        return session.exec(select(Entity).where(Entity.entity_type == "company")).all()

    def get_institutions(self, session: Session):
        return session.exec(
            select(Entity).where(Entity.entity_type == "institution")
        ).all()

    def get_entities_with_founders(self, session: Session):
        return session.exec(
            select(Entity).where(Entity.founders != None)  # type: ignore
        ).all()

    def get_ai_entities(self, session: Session):
        return session.exec(select(Entity).where(Entity.is_ai_related == True)).all()

    def count(self, session: Session) -> int:
        return session.exec(select(Entity)).all().__len__()

    def update(self, session: Session, entity_id: int, data: dict):
        entity = self.get_by_id(session, entity_id)
        if not entity:
            return None

        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

        session.commit()
        session.refresh(entity)
        return entity

    def delete(self, session: Session, entity_id: int):
        entity = self.get_by_id(session, entity_id)
        if not entity:
            return False

        session.delete(entity)
        session.commit()
        return True

    def delete_all(self, session: Session):
        session.exec(select(Entity))
        session.query(Entity).delete()
        session.commit()
