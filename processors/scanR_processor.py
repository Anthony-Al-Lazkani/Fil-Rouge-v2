"""
Processeur ScanR enrichi.
Extrait les données géographiques, temporelles, les liens web et les leaders (Directeurs/Responsables).
"""

from sqlmodel import Session, select
from models import Entity, ResearchItem, Source, Author, Affiliation

class ScanRProcessor:
    def __init__(self, session: Session):
        self.session = session
        self.scanr_source = self._get_or_create_source("scanr", "public_research")
        self.epo_source = self._get_or_create_source("epo_ops", "patent")

    def _get_or_create_source(self, name: str, type_name: str):
        source = self.session.exec(select(Source).where(Source.name == name)).first()
        if not source:
            source = Source(name=name, type=type_name)
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        return source

    def process_leaders(self, entity_id: int, leaders_data: list):
        """Extrait les leaders et crée les auteurs et affiliations correspondantes."""
        for leader in leaders_data:
            first_name = leader.get("firstName")
            last_name = leader.get("lastName")
            if not (first_name and last_name):
                continue
            
            full_name = f"{first_name} {last_name}".upper()
            # On utilise le slug standardisé : person_prenom_nom
            clean_first = first_name.lower().strip()
            clean_last = last_name.lower().strip()
            a_slug = f"person_{clean_first}_{clean_last}"
            
            # 1. Vérifier si l'auteur existe déjà
            author = self.session.exec(select(Author).where(Author.external_id == a_slug)).first()
            if not author:
                author = Author(
                    full_name=full_name,
                    external_id=a_slug,
                    publication_count=0
                )
                self.session.add(author)
                self.session.flush() # Récupère l'ID sans commiter

            # 2. Créer l'affiliation avec le rôle de leader
            # Note: research_item_id reste NULL car c'est une relation structurelle, pas liée à une publi
            existing_aff = self.session.exec(
                select(Affiliation).where(
                    Affiliation.author_external_id == a_slug,
                    Affiliation.entity_id == entity_id,
                    Affiliation.role == "Leader"
                )
            ).first()

            if not existing_aff:
                self.session.add(Affiliation(
                    entity_id=entity_id,
                    author_external_id=a_slug,
                    role="Leader",
                    source_name="scanr_leader_extraction"
                ))

    def process_organizations(self, orgs: list) -> int:
        count = 0
        for data in orgs:
            raw = data.get("raw", {})
            ext_id = str(data["external_id"])
            
            existing_entity = self.session.exec(
                select(Entity).where(Entity.external_id == ext_id)
            ).first()
            
            # --- CRÉATION / RÉCUPÉRATION DE L'ENTITÉ ---
            if not existing_entity:
                label_data = raw.get("label", {})
                full_name = label_data.get("fr") or label_data.get("default") or label_data.get("en")
                
                acronym_data = raw.get("acronym", {})
                acronym = acronym_data.get("fr") or acronym_data.get("default") or acronym_data.get("en")
                display_name = f"{acronym} - {full_name}" if acronym else full_name

                email = raw.get("email")
                twitter = next((sm.get("url") for sm in raw.get("socialMedias", []) if sm.get("type") == "twitter"), None)
                links = raw.get("links", [])
                website = None
                if links:
                    website = next((l.get("url") for l in links if l.get("type") == "main"), links[0].get("url"))

                addr = raw.get("address", [{}])[0]
                city = addr.get("city")
                country = addr.get("country", "France")

                existing_entity = Entity(
                    source_id=self.scanr_source.id,
                    external_id=ext_id,
                    name=full_name or "Nom inconnu",
                    display_name=display_name,
                    type=data["type"], 
                    city=city,
                    country_code=country,
                    website=website,
                    founded_date=str(raw.get("creationYear")) if raw.get("creationYear") else None,
                    operating_status=raw.get("status"),
                    is_ai_related=True,
                    raw={**raw, "_extracted_email": email, "_extracted_twitter": twitter}
                )
                self.session.add(existing_entity)
                self.session.flush() # Pour avoir l'ID pour les leaders

            # --- TRAITEMENT DES LEADERS (Hervé Glotin & co) ---
            if raw.get("leaders"):
                self.process_leaders(existing_entity.id, raw["leaders"])

            # --- GESTION DES BREVETS ---
            for p_data in data.get("patents", []):
                p_ext_id = str(p_data["external_id"])
                existing_patent = self.session.exec(
                    select(ResearchItem).where(ResearchItem.external_id == p_ext_id)
                ).first()
                
                if not existing_patent:
                    self.session.add(ResearchItem(
                        source_id=self.epo_source.id,
                        external_id=p_ext_id,
                        title=p_data["title"],
                        type="patent",
                        is_open_access=False,
                        raw={"discovery_source": "scanr", "owner_id": ext_id, "original_data": p_data}
                    ))

            count += 1
            
        self.session.commit()
        return count