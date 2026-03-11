"""
Processeur épuré pour les organisations (Universités, Labos, Entreprises).

Features:
- Unifie le stockage dans la table Entity.
- Gère la déduplication par external_id et ROR.
- Fusionne les attributs académiques et économiques.
"""

from sqlmodel import Session, select
from database import engine
from models import Entity, Source

class InstitutionProcessor:
    def __init__(self):
        self.session = Session(engine)
        # Gestion de la source OpenAlex
        source = self.session.exec(select(Source).where(Source.name == "openalex")).first()
        if not source:
            source = Source(name="openalex", type="academic")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    def process_institutions(self, institutions: list) -> int:
        """Traite et insère les institutions en tant qu'entités unifiées."""
        count = 0
        for inst in institutions:
            ext_id = inst.get("external_id")
            ror = inst.get("ror")

            # Check doublon par external_id ou ROR
            existing = None
            if ext_id:
                existing = self.session.exec(select(Entity).where(Entity.external_id == ext_id)).first()
            if not existing and ror:
                existing = self.session.exec(select(Entity).where(Entity.ror == ror)).first()

            if existing:
                continue

            # Création de l'entité épurée (Fusion Académique/Entreprise)
            new_entity = Entity(
                source_id=self.source_id,
                external_id=ext_id,
                ror=ror,
                name=inst.get("display_name", "Unknown"),
                display_name=inst.get("display_name"),
                acronyms=inst.get("display_name_acronyms", []),
                type=inst.get("type"), # ex: 'education', 'company'
                country_code=inst.get("country_code"),
                city=inst.get("geo", {}).get("city") if inst.get("geo") else None,
                website=inst.get("homepage_url"),
                works_count=inst.get("works_count", 0),
                cited_by_count=inst.get("cited_by_count", 0),
                raw=inst
            )
            
            self.session.add(new_entity)
            count += 1
            
            if count % 100 == 0:
                self.session.commit()

        self.session.commit()
        return count