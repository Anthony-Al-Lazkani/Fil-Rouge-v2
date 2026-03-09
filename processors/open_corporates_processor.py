from database import get_session
from services.organization_service import OrganizationService
from services.source_service import SourceService
from schemas.organization import OrganizationCreate
from schemas.source import SourceCreate
from typing import List, Dict, Any

class OpenCorporatesProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.source_service = SourceService()
        self.org_service = OrganizationService()

        self.oc_source = self.source_service.create(
            self.session,
            SourceCreate(
                name="opencorporates",
                type="legal_registry",
                base_url="https://opencorporates.com/",
            ),
        )

    def process_companies(self, companies: List[Dict[str, Any]]) -> int:
        processed_count = 0

        for co_data in companies:
            # On vérifie si elle existe déjà via external_id (SIREN)
            existing = self.org_service.get_by_external_id(self.session, co_data["external_id"])
            if existing:
                continue

            org_create = OrganizationCreate(
                source_id=self.oc_source.id,
                external_id=co_data["external_id"],
                name=co_data["name"],
                type=co_data["type"],
                country="France",
                founded_date=co_data["founded_date"],
                operating_status=co_data["operating_status"],
                is_ai_related=True,
                raw=co_data["raw"]
            )
            
            self.org_service.create(self.session, org_create)
            processed_count += 1

        return processed_count