from database import get_session
from services.institution_service import InstitutionService
from services.source_service import SourceService
from schemas.institution import InstitutionCreate
from schemas.source import SourceCreate
from typing import List, Dict, Any


class InstitutionProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.institution_service = InstitutionService()
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
        """Check if an institution already exists in the DB"""
        return (
            self.institution_service.get_by_external_id(self.session, external_id)
            is not None
        )

    def create_institution(self, inst_data: Dict[str, Any]):
        """Create institution in database"""
        institution = InstitutionCreate(
            source_id=self.openalex_source.id,
            external_id=inst_data.get("external_id"),
            ror=inst_data.get("ror"),
            display_name=inst_data.get("display_name", ""),
            display_name_acronyms=inst_data.get("display_name_acronyms", []),
            display_name_alternatives=inst_data.get("display_name_alternatives", []),
            country_code=inst_data.get("country_code"),
            type=inst_data.get("type"),
            homepage_url=inst_data.get("homepage_url"),
            works_count=inst_data.get("works_count", 0),
            cited_by_count=inst_data.get("cited_by_count", 0),
            associated_institutions=inst_data.get("associated_institutions", []),
            counts_by_year=inst_data.get("counts_by_year", []),
        )
        return self.institution_service.create(self.session, institution)

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
