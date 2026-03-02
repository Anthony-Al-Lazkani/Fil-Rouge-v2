from database import get_session
from models import ResearchItem
from services.affiliation_service import AffiliationService
from services.author_service import AuthorService
from services.research_item_service import ResearchItemService
from services.organization_service import OrganizationService
from services.institution_service import InstitutionService
from schemas.affiliation import AffiliationCreate
from models.author import Author
from models.organization import Organization
from models.institution import Institution
from sqlmodel import select


class AffiliationProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.affiliation_service = AffiliationService()
        self.author_service = AuthorService()
        self.item_service = ResearchItemService()
        self.organization_service = OrganizationService()
        self.institution_service = InstitutionService()

    def find_organization(self, external_id: str = None, ror: str = None):
        """Find organization by external_id or ror"""
        if external_id:
            return self.session.exec(
                select(Organization).where(Organization.external_id == external_id)
            ).first()
        if ror:
            return self.session.exec(
                select(Organization).where(Organization.ror == ror)
            ).first()
        return None

    def find_institution(self, external_id: str = None, ror: str = None):
        """Find institution by external_id or ror"""
        if external_id:
            return self.session.exec(
                select(Institution).where(Institution.external_id == external_id)
            ).first()
        if ror:
            return self.session.exec(
                select(Institution).where(Institution.ror == ror)
            ).first()
        return None

    def create_affiliation(
        self, author_id: int, research_item_id: int, aff_data: dict, role: str = None
    ):
        """Create an affiliation record"""
        external_id = aff_data.get("id")
        ror = aff_data.get("ror")
        display_name = aff_data.get("display_name")
        country_code = aff_data.get("country_code")
        affiliation_type = aff_data.get("type")

        organization_id = None
        institution_id = None

        org = self.find_organization(external_id=external_id, ror=ror)
        if org:
            organization_id = org.id
        else:
            inst = self.find_institution(external_id=external_id, ror=ror)
            if inst:
                institution_id = inst.id

        aff_data_create = AffiliationCreate(
            author_id=author_id,
            research_item_id=research_item_id,
            organization_id=organization_id,
            institution_id=institution_id,
            external_id=external_id,
            display_name=display_name,
            ror=ror,
            country_code=country_code,
            affiliation_type=affiliation_type,
            role=role,
        )
        return self.affiliation_service.create(self.session, aff_data_create)

    def process_research_item(self, research_item_id: int):
        """Process a single research item and create affiliations"""
        item = self.session.exec(
            select(ResearchItem).where(ResearchItem.id == research_item_id)
        ).first()

        if not item:
            return 0

        metrics = item.metrics or {}
        authors_data = metrics.get("authors", [])
        author_ids = metrics.get("author_ids", [])

        created_count = 0

        for idx, author_data in enumerate(authors_data):
            author_external_id = author_data.get("author_id")
            if not author_external_id:
                continue

            author = self.session.exec(
                select(Author).where(Author.external_id == author_external_id)
            ).first()

            if not author:
                continue

            role = None
            if author_data.get("roles"):
                role = author_data["roles"][0] if author_data["roles"] else None

            affiliations = author_data.get("affiliations", [])
            if not affiliations:
                self.create_affiliation(author.id, item.id, {}, role)
                created_count += 1
                continue

            for aff in affiliations:
                self.create_affiliation(author.id, item.id, aff, role)
                created_count += 1

        return created_count

    def process_all_research_items(self, limit: int = None):
        """Process all research items and create affiliations"""
        query = select(ResearchItem)
        if limit:
            query = query.limit(limit)

        items = self.session.exec(query).all()
        total_created = 0

        for item in items:
            count = self.process_research_item(item.id)
            total_created += count

        return total_created
