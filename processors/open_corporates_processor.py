from database import get_session
from services.organization_service import OrganizationService
from schemas.organization import OrganizationCreate
from typing import List, Dict, Any

class OpenCorporatesProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.org_service = OrganizationService()

    def process_companies(self, companies: List[Dict[str, Any]]) -> int:
        processed_count = 0
        if not companies:
            print("[WARN] Processor : Aucune donnée reçue du Crawler.")
            return 0

        for co in companies:
            siren = co.get("company_number")
            
            # Extraction Founders (Officers)
            officers = co.get("officers") or []
            founder_names = [o.get("officer", {}).get("name") for o in officers if o.get("officer")]

            # Extraction Website (Data section)
            website = None
            data_sec = co.get("data")
            if data_sec:
                for entry in data_sec.get("most_recent") or []:
                    datum = entry.get("datum", {})
                    if datum.get("title") == "Website":
                        website = datum.get("description")

            org_create = OrganizationCreate(
                source="opencorporates",
                external_id=siren,
                name=co.get("name"),
                clean_name=co.get("name").strip().upper() if co.get("name") else None,
                type=co.get("company_type"),
                country="France",
                founded_date=co.get("incorporation_date"),
                operating_status=co.get("current_status"),
                website=website,
                founders=founder_names,
                number_of_founders=len(founder_names),
                is_ai_related=True,
                raw=co
            )

            # On laisse le service gérer les doublons (return existing)
            self.org_service.create(self.session, org_create)
            processed_count += 1

        return processed_count