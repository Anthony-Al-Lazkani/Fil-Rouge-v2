"""
Processeur épuré pour OpenCorporates.

Features:
- Ingestion des données légales des entreprises.
- Identification unique via le registre légal (numéro d'entreprise).
- Mapping direct vers le modèle Entity.
"""

from sqlmodel import Session, select
from database import engine
from models import Entity, Source

class OpenCorporatesProcessor:
    def __init__(self):
        self.session = Session(engine)
        # Initialisation ou récupération de la source
        source = self.session.exec(
            select(Source).where(Source.name == "opencorporates")
        ).first()
        if not source:
            source = Source(
                name="opencorporates",
                type="legal_registry",
                base_url="https://opencorporates.com/"
            )
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    def process_companies(self, companies: list) -> int:
        """Traite et insère les entreprises issues du registre légal."""
        processed_count = 0

        for co_data in companies:
            ext_id = co_data.get("external_id")
            if not ext_id: continue

            # Déduplication par external_id
            existing = self.session.exec(
                select(Entity).where(Entity.external_id == ext_id)
            ).first()
            if existing: continue

            try:
                # Mapping direct vers Entity épuré
                new_entity = Entity(
                    source_id=self.source_id,
                    external_id=ext_id,
                    name=co_data.get("name"),
                    type=co_data.get("type", "company"),
                    country=co_data.get("jurisdiction"),
                    country_code=co_data.get("jurisdiction_code"),
                    founded_date=co_data.get("founded_date"),
                    operating_status=co_data.get("operating_status"),
                    is_ai_related=True, # Les crawlers ciblent déjà des boîtes IA
                    raw=co_data.get("raw", co_data)
                )
                
                self.session.add(new_entity)
                processed_count += 1

                if processed_count % 100 == 0:
                    self.session.commit()

            except Exception as e:
                self.session.rollback()
                print(f"Erreur OpenCorporates pour {ext_id}: {e}")
                continue

        self.session.commit()
        return processed_count