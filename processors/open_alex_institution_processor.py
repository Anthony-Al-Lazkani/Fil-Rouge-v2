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
            
        # Flush pour garantir que tous les IDs techniques sont générés
        self.session.flush()



        # ÉTAPE 2 : Résolution de la hiérarchie (Parent/Child)  --- pour prendre en compte les métadonnées d'affiliations des entités.
        for inst in institutions:
            self._resolve_hierarchy(inst)

        self.session.commit()
        return count

    def _get_existing_entity(self, ext_id, ror):
        """Recherche une entité par ROR ou external_id."""
        if ror:
            res = self.session.exec(select(Entity).where(Entity.ror == ror)).first()
            if res: return res
        return self.session.exec(select(Entity).where(Entity.external_id == ext_id)).first()

    def _resolve_hierarchy(self, inst_data):
        """Définit le parent_id si une relation 'child' est détectée dans OpenAlex."""
        raw = inst_data.get("raw", {})
        associated = raw.get("associated_institutions", [])
        
        # Si cette institution est un 'child', on cherche son 'parent'
        for assoc in associated:
            if assoc.get("relationship") == "parent":
                parent_ext_id = assoc.get("id").split("/")[-1] # Extrait 'I19820366'
                parent_ror = assoc.get("ror")
                
                # On cherche le parent en base
                parent = self._get_existing_entity(parent_ext_id, parent_ror)
                
                if parent:
                    # On cherche l'enfant actuel en base
                    child = self._get_existing_entity(inst_data["external_id"], inst_data.get("ror"))
                    if child and child.id != parent.id:
                        child.parent_id = parent.id
                        self.session.add(child)