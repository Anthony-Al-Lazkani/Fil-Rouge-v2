from database import get_session
from services.organization_service import OrganizationService
from services.source_service import SourceService
from schemas.organization import OrganizationCreate
from services.research_item_service import ResearchItemService
from schemas.source import SourceCreate
from typing import List, Dict, Any

class ScanRProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.org_service = OrganizationService()
        self.item_service = ResearchItemService()
        self.source_service = SourceService()

        # On s'assure d'avoir les deux sources en base
        self.scanr_source = self.source_service.create(self.session, SourceCreate(name="scanr", type="public_research"))
        self.epo_source = self.source_service.create(self.session, SourceCreate(name="epo_ops", type="patent"))

    def process_organizations(self, orgs: List[Dict[str, Any]]) -> int:
        count = 0
        for data in orgs:
            # 1. Création de l'Organisation
            org = self.org_service.create(self.session, OrganizationCreate(
                source_id=self.scanr_source.id,
                external_id=data["external_id"],
                name=data["name"],
                type=data["type"],
                city=data["city"],
                raw=data["raw"]
            ))

            # 2. Création des ResearchItems (Brevets) liés
            for p_data in data.get("patents", []):
                try:
                    self.item_service.create(self.session, ResearchItemCreate(
                        source_id=self.epo_source.id,
                        external_id=p_data["external_id"],
                        title=p_data["title"],
                        type="patent",
                        raw={"discovery_source": "scanr", "owner_siren": data["external_id"]}
                    ))
                except:
                    continue # Ignore si le brevet existe déjà (unique=true sur external_id)

            count += 1
        return count