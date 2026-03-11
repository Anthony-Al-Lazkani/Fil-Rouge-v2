from database import get_session
from services.entity_service import EntityService
from services.source_service import SourceService
from schemas.entity import EntityCreate
from services.research_item_service import ResearchItemService, ResearchItemCreate
from schemas.source import SourceCreate
from typing import List, Dict, Any


class ScanRProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.entity_service = EntityService()
        self.item_service = ResearchItemService()
        self.source_service = SourceService()

        self.scanr_source = self.source_service.create(
            self.session, SourceCreate(name="scanr", type="public_research")
        )
        self.epo_source = self.source_service.create(
            self.session, SourceCreate(name="epo_ops", type="patent")
        )

    def process_organizations(self, orgs: List[Dict[str, Any]]) -> int:
        count = 0
        for data in orgs:
            entity = self.entity_service.create(
                self.session,
                EntityCreate(
                    source_id=self.scanr_source.id,
                    external_id=data["external_id"],
                    name=data["name"],
                    entity_type="institution",
                    type=data["type"],
                    city=data["city"],
                    raw=data["raw"],
                ),
            )

            for p_data in data.get("patents", []):
                try:
                    self.item_service.create(
                        self.session,
                        ResearchItemCreate(
                            source_id=self.epo_source.id,
                            external_id=p_data["external_id"],
                            title=p_data["title"],
                            type="patent",
                            raw={
                                "discovery_source": "scanr",
                                "owner_siren": data["external_id"],
                            },
                        ),
                    )
                except:
                    continue

            count += 1
        return count
