"""
Processeur optimisé pour OpenCorporates.
Extrait le maximum de métadonnées légales : statut, ville, année et activité.
"""
from sqlmodel import Session, select
from models import Entity, Source
from datetime import datetime

class OpenCorporatesProcessor:
    def __init__(self, session: Session):
        self.session = session
        source = self.session.exec(
            select(Source).where(Source.name == "opencorporates")
        ).first()
        if not source:
            source = Source(name="opencorporates", type="legal_registry")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    def process_companies(self, companies: list) -> int:
        processed_count = 0

        for co_data in companies:
            raw = co_data.get("raw", co_data)
            ext_id = raw.get("company_number")
            if not ext_id: continue

            existing = self.session.exec(
                select(Entity).where(Entity.external_id == ext_id)
            ).first()
            if existing: continue

            # --- EXTRACTION SÉCURISÉE ---
            
            # 1. Ville (Vérification de l'existence de l'adresse)
            address = raw.get("registered_address") or {}
            city = address.get("locality") if isinstance(address, dict) else None

            # 2. Année de création
            inc_date = raw.get("incorporation_date")
            founded_year = None
            if inc_date and isinstance(inc_date, str):
                try:
                    founded_year = int(inc_date.split("-")[0])
                except (ValueError, IndexError):
                    founded_year = None

            # 3. Statut
            status = raw.get("current_status", "Unknown")
            is_inactive = raw.get("inactive", False)
            operating_status = f"{status} ({'Inactive' if is_inactive else 'Active'})"

            # 4. Description (Vérification des codes industrie)
            industry_codes = raw.get("industry_codes") or []
            description = None
            if industry_codes and len(industry_codes) > 0:
                # On sécurise l'accès au premier code
                first_code = industry_codes[0].get("industry_code") or {}
                description = first_code.get("description")

            # 5. Acronymes
            alt_names = [n.get("company_name") for n in (raw.get("alternative_names") or []) if n.get("company_name")]


            # 6. Normalisation du type (On force 'company' pour la cohérence)
            legal_form = raw.get("company_type", "company")
            normalized_type = "company" 

            # 7. Normalisation des industries (On injecte IA par défaut)
            # On peut aussi combiner avec la description si elle existe
            inferred_industries = ["Intelligence Artificielle"]
            if description:
                inferred_industries.append(description)


            # --- MAPPING ---
            new_entity = Entity(
                source_id=self.source_id,
                external_id=str(ext_id),
                name=raw.get("name"),
                acronyms=alt_names,
                type=normalized_type, # <--- Toujours 'company'
                country_code=str(raw.get("jurisdiction_code", "UN")).upper()[:2], # Limite à 2 chars,
                city=city,
                founded_year=founded_year,
                operating_status=operating_status,
                industries=inferred_industries, # <--- Plus de champ vide
                description=description,
                is_ai_related=True,
                raw={
                    **raw,
                    "_original_legal_type": legal_form # On garde le statut précis ici au cas où
                }
            )
            
            self.session.add(new_entity)
            processed_count += 1

        self.session.commit()
        return processed_count