"""
Processeur épuré pour ScanR.

Features:
- Ingestion double : Organisations (Entity) et Brevets (ResearchItem).
- Gestion des sources scanR et epo_ops (brevets).
- Mapping direct vers les modèles sans schémas intermédiaires.
"""

from sqlmodel import Session, select
from database import engine
from models import Entity, ResearchItem, Source

class ScanRProcessor:
    def __init__(self):
        self.session = Session(engine)
        
        # Initialisation des deux sources liées à ScanR
        self.scanr_source = self._get_or_create_source("scanr", "public_research")
        self.epo_source = self._get_or_create_source("epo_ops", "patent")

    def _get_or_create_source(self, name: str, type: str):
        source = self.session.exec(select(Source).where(Source.name == name)).first()
        if not source:
            source = Source(name=name, type=type)
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        return source

    def process_organizations(self, orgs: list) -> int:
        """Traite les organisations et leurs brevets associés."""
        count = 0
        for data in orgs:
            # 1. Insertion de l'entité (Labo ou Entreprise)
            existing_entity = self.session.exec(
                select(Entity).where(Entity.external_id == data["external_id"])
            ).first()
            
            if not existing_entity:
                entity = Entity(
                    source_id=self.scanr_source.id,
                    external_id=data["external_id"],
                    name=data["name"],
                    type=data["type"], # ex: 'institution' ou 'company'
                    city=data.get("city"),
                    raw=data.get("raw", data)
                )
                self.session.add(entity)

            # 2. Insertion des brevets liés
            for p_data in data.get("patents", []):
                existing_patent = self.session.exec(
                    select(ResearchItem).where(ResearchItem.external_id == p_data["external_id"])
                ).first()
                
                if not existing_patent:
                    patent = ResearchItem(
                        source_id=self.epo_source.id,
                        external_id=p_data["external_id"],
                        title=p_data["title"],
                        type="patent",
                        raw={
                            "discovery_source": "scanr",
                            "owner_id": data["external_id"],
                            "details": p_data
                        }
                    )
                    self.session.add(patent)

            count += 1
            if count % 50 == 0:
                self.session.commit()

        self.session.commit()
        return count