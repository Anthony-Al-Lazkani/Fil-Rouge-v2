"""
Processeur dédié aux institutions OpenAlex.
Remplit la table Entity avec les métadonnées académiques mondiales.
"""
from sqlmodel import Session, select
from models import Entity, Source

class OpenAlexInstitutionProcessor:
    def __init__(self, session: Session):
        self.session = session
        # Initialisation de la source spécifique
        source = self.session.exec(select(Source).where(Source.name == "openalex")).first()
        if not source:
            source = Source(name="openalex", type="academic", base_url="https://openalex.org/")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    def process_institutions(self, institutions: list) -> int:
        """Traite les dictionnaires issus du crawler OpenAlex Institutions."""
        count = 0
        for inst in institutions:
            ext_id = inst.get("external_id")
            ror = inst.get("ror")

            if not ext_id: continue

            # Déduplication par ID ou ROR
            existing = None
            if ror:
                existing = self.session.exec(select(Entity).where(Entity.ror == ror)).first()
            if not existing:
                existing = self.session.exec(select(Entity).where(Entity.external_id == ext_id)).first()

            if existing: continue

            # Création de l'entité (Structure OpenAlex à plat)
            new_entity = Entity(
                source_id=self.source_id,
                external_id=ext_id,
                ror=ror,
                name=inst.get("display_name", "Unknown"),
                display_name=inst.get("display_name"),
                acronyms=inst.get("acronyms", []),
                type=inst.get("type"),
                country_code=inst.get("country_code"),
                city=inst.get("city"), # Souvent None dans l'API simplifiée, mais dispo dans raw
                website=inst.get("homepage_url"),
                works_count=inst.get("works_count", 0),
                cited_by_count=inst.get("cited_by_count", 0),
                raw=inst
            )
            
            self.session.add(new_entity)
            count += 1
            
        self.session.commit()
        return count