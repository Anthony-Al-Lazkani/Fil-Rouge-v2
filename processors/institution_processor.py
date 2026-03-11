from database import get_session
from services.entity_service import EntityService
from services.source_service import SourceService
from schemas.entity import EntityCreate
from schemas.source import SourceCreate
from typing import List, Dict, Any


class InstitutionProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.entity_service = EntityService()
        self.source_service = SourceService()

        self.openalex_source = self.source_service.create(
            self.session,
            SourceCreate(
                name="openalex",
                type="academic",
                base_url="https://openalex.org/",
            ),
        )

    def exists(self, external_id: str) -> bool:
        """Check if an entity already exists in the DB"""
        return (
            self.entity_service.get_by_external_id(self.session, external_id)
            is not None
        )

    def create_institution(self, inst_data: Dict[str, Any]):
        """Create institution in database as Entity"""
        entity = EntityCreate(
            source_id=self.openalex_source.id,
            external_id=inst_data.get("external_id"),
            ror=inst_data.get("ror"),
            name=inst_data.get("display_name", ""),
            display_name=inst_data.get("display_name"),
            display_name_acronyms=inst_data.get("display_name_acronyms", []),
            display_name_alternatives=inst_data.get("display_name_alternatives", []),
            entity_type="institution",
            country_code=inst_data.get("country_code"),
            type=inst_data.get("type"),
            homepage_url=inst_data.get("homepage_url"),
            works_count=inst_data.get("works_count", 0),
            cited_by_count=inst_data.get("cited_by_count", 0),
            associated_entities=inst_data.get("associated_institutions", []),
            counts_by_year=inst_data.get("counts_by_year", []),
        )
        return self.entity_service.create(self.session, entity)

    def process_institutions(self, institutions: List[Dict[str, Any]]) -> int:
        """Process a list of institutions and insert them into the database"""
        processed_count = 0

        for inst_data in institutions:
            external_id = inst_data.get("external_id")

            if external_id and self.exists(external_id):
                continue

            self.create_institution(inst_data)
            processed_count += 1

        return processed_count
