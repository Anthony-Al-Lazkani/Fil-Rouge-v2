from database import get_session
from services.organization_service import OrganizationService
from services.research_item_service import ResearchItemService
from schemas.organization import OrganizationCreate
from schemas.research_item import ResearchItemCreate
from typing import List, Dict, Any

class ScanRProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.org_service = OrganizationService()
        self.item_service = ResearchItemService()

    def process_organizations(self, orgs: List[Dict[str, Any]]) -> int:
        count = 0
        for data in orgs:
            # 1. Création de l'Organisation (Mapping strict avec ton modèle)
            org_create = OrganizationCreate(
                source="scanr",
                external_id=data["external_id"],
                name=data["name"],
                clean_name=data["name"].strip().upper(),
                type=data["type"],
                city=data["city"],
                founded_date=data["founded_date"],
                operating_status=data["operating_status"],
                is_ai_related=True,
                raw=data["raw"]
            )
            
            self.org_service.create(self.session, org_create)

            # 2. Extraction et création des brevets (ResearchItems)
            # Les brevets sont nichés dans le raw data de ScanR
            raw_source = data.get("raw", {})
            patents = raw_source.get("patents", [])
            
            for p in patents:
                try:
                    # Ici on peut utiliser un ID de source fixe pour EPO si tu veux
                    # Ou simplement marquer la provenance dans le raw du ResearchItem
                    item_create = ResearchItemCreate(
                        source_id=2, # Assure-toi que l'ID 2 correspond à EPO ou ScanR dans ta table Source
                        external_id=str(p.get("id")),
                        title=p.get("title", {}).get("fr") or p.get("title", {}).get("default"),
                        type="patent",
                        raw={"owner_siren": data["external_id"], "scanr_data": p}
                    )
                    self.item_service.create(self.session, item_create)
                except Exception:
                    continue # Doublon de brevet probable

            count += 1
        return count