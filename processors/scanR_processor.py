"""
Processeur ScanR enrichi.
Extrait les données géographiques, temporelles, les liens web, 
les leaders (Directeurs) et gère la hiérarchie des tutelles.
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
            rnsr_domains = raw.get("rnsr_domains", [])
            industries_to_use = [d for d in rnsr_domains if d]
            
            if not industries_to_use:
                industries_to_use = raw.get("categories", [])

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
                country = addr.get("iso3") or addr.get("country", "France")

                # Extraction des domaines -> industries
                rnsr_domains = raw.get("rnsr_domains", [])
                industries = [d for d in rnsr_domains if d] 

                # Extraction des tutelles -> parent_entities
                # On récupère les labels des établissements de tutelle
                tutelles_labels = [
                    rel.get("label") 
                    for rel in raw.get("institutions", []) 
                    if rel.get("relationType") == "établissement tutelle"
                ]

                existing_entity = Entity(
                    source_id=self.scanr_source.id,
                    external_id=ext_id,
                    name=full_name or "Nom inconnu",
                    display_name=display_name,
                    type=data.get("type", "research_structure"), 
                    city=city,
                    country_code=addr.get("iso3") or "FRA",
                    website=website,
                    industries=list(industries_to_use),
                    founded_date=str(raw.get("creationYear")) if raw.get("creationYear") else None,
                    operating_status=raw.get("status"),
                    is_ai_related=True, # Puisque extrait via pipeline IA
                    raw={**raw, 
                         "_extracted_email": email, 
                         "_extracted_twitter": twitter,
                         "tutelles": tutelles_labels,
                         "is_french": raw.get("isFrench", True)
                    }    
                )
                self.session.add(existing_entity)
                self.session.flush() 


                # --- RÉSOLUTION DE LA HIÉRARCHIE (Lien Parent via Tutelles) ---
                for inst_rel in raw.get("institutions", []):
                    if inst_rel.get("relationType") == "établissement tutelle":
                        p_ext_id = str(inst_rel.get("structure"))
                        # On cherche si la tutelle (ex: Inria) est déjà présente en base
                        parent = self.session.exec(
                            select(Entity).where(Entity.external_id == p_ext_id)
                        ).first()
                        if parent:
                            existing_entity.parent_id = parent.id
                            # Pas besoin de session.add, existing_entity est déjà suivi

            # --- TRAITEMENT DES LEADERS (Hervé Glotin & co) ---
            if raw.get("leaders"):
                self.process_leaders(existing_entity.id, raw["leaders"])

            # --- GESTION DES BREVETS (ALIGNEMENT STRICT) ---
            for p_data in data.get("patents", []):
                p_ext_id = str(p_data.get("external_id"))
                if not p_ext_id: continue
                
                existing_patent = self.session.exec(
                    select(ResearchItem).where(ResearchItem.external_id == p_ext_id)
                ).first()
                
                # On définit la thématique ici pour être sûr de l'alignement
                # On tire la valeur DIRECTEMENT de ce qu'on vient d'écrire dans l'entité
                tags_a_utiliser = existing_entity.industries 

                if not existing_patent:
                    p_title = p_data.get("title")
                    if isinstance(p_title, dict):
                        p_title = p_title.get("fr") or p_title.get("default")
                    
                    self.session.add(ResearchItem(
                        source_id=self.epo_source.id,
                        external_id=p_ext_id,
                        title=p_title,
                        type="patent",
                        is_open_access=False,
                        # EGALITE STRICTE ICI
                        topics=tags_a_utiliser, 
                        raw={"discovery_source": "scanr", "owner_id": ext_id, "original_data": p_data}
                    ))
                else:
                    # MISE À JOUR : On force l'alignement même si le brevet existait
                    existing_patent.topics = tags_a_utiliser
                    self.session.add(existing_patent)

            count += 1
            
        self.session.commit()
        return count