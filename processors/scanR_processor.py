"""
Processeur ScanR enrichi.
Extrait les données géographiques, temporelles et les liens web.
"""

from sqlmodel import Session, select
from models import Entity, ResearchItem, Source

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

    def process_organizations(self, orgs: list) -> int:
        count = 0
        for data in orgs:
            raw = data.get("raw", {})
            ext_id = str(data["external_id"])
            
            existing_entity = self.session.exec(
                select(Entity).where(Entity.external_id == ext_id)
            ).first()
            
            if not existing_entity:
                # --- EXTRACTION ENRICHIE ---
                
                # Dans ton ScanRProcessor, affine l'extraction comme ceci :

                # 1. Nom et Acronyme (Gestion du FR/EN/Default)
                label_data = raw.get("label", {})
                full_name = label_data.get("fr") or label_data.get("default") or label_data.get("en")
                
                acronym_data = raw.get("acronym", {})
                acronym = acronym_data.get("fr") or acronym_data.get("default") or acronym_data.get("en")
                
                # On stocke l'acronyme proprement dans la colonne dédiée si elle existe
                # Sinon on l'inclut dans le display_name
                display_name = f"{acronym} - {full_name}" if acronym else full_name

                # 2. Email et Réseaux Sociaux (dans le champ raw, mais on peut extraire l'essentiel)
                email = raw.get("email")
                twitter = next((sm.get("url") for sm in raw.get("socialMedias", []) if sm.get("type") == "twitter"), None)
                links = raw.get("links", [])
                website = None
                if links:
                    website = next((l.get("url") for l in links if l.get("type") == "main"), links[0].get("url"))

                # 3. Géographie précise
                addr = raw.get("address", [{}])[0]
                city = addr.get("city")
                country = addr.get("country", "France")

                entity = Entity(
                    source_id=self.scanr_source.id,
                    external_id=ext_id,
                    name=full_name or "Nom inconnu",
                    display_name=display_name,
                    type=data["type"], 
                    city=city,
                    country_code=country,
                    website=website,
                    founded_date=str(raw.get("creationYear")) if raw.get("creationYear") else None,
                    operating_status=raw.get("status"), # 'old' ou 'active'
                    is_ai_related=True,
                    raw={
                        **raw,
                        "_extracted_email": email,
                        "_extracted_twitter": twitter
                    }
                )
                self.session.add(entity)

            # 2. Gestion des brevets (inchangée mais nécessaire)
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