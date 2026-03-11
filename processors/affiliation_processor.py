from database import get_session
from models import ResearchItem, Entity
from models.source import Source
from services.affiliation_service import AffiliationService
from services.author_service import AuthorService
from services.research_item_service import ResearchItemService
from services.entity_service import EntityService
from schemas.affiliation import AffiliationCreate
from models.author import Author
from sqlmodel import select


class AffiliationProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.affiliation_service = AffiliationService()
        self.author_service = AuthorService()
        self.item_service = ResearchItemService()
        self.entity_service = EntityService()

    def find_entity(self, external_id: str = None, ror: str = None):
        """Find entity by external_id or ror"""
        if external_id:
            if external_id.startswith("https://openalex.org/"):
                ext_id = external_id.replace("https://openalex.org/", "")
            else:
                ext_id = external_id
            return self.session.exec(
                select(Entity).where(Entity.external_id == ext_id)
            ).first()
        if ror:
            if ror.startswith("https://ror.org/"):
                ror = ror.replace("https://ror.org/", "")
            return self.session.exec(select(Entity).where(Entity.ror == ror)).first()
        return None

    def get_source_name(self, source_id: int) -> str:
        """Get source name by ID"""
        source = self.session.exec(select(Source).where(Source.id == source_id)).first()
        return source.name if source else "unknown"

    def create_affiliation(
        self,
        author_external_id: str,
        research_item_id: int,
        research_item_data: dict,
        author_full_name: str,
        author_orcid: str,
        aff_data: dict,
        role: str = None,
    ):
        """Create an affiliation record with comprehensive information"""
        entity_external_id = aff_data.get("id")
        entity_name = aff_data.get("display_name")
        entity_ror = aff_data.get("ror")
        entity_country_code = aff_data.get("country_code")
        entity_type = aff_data.get("type")

        entity = self.find_entity(external_id=entity_external_id, ror=entity_ror)

        if entity:
            entity_id = entity.id
            entity_external_id = entity.external_id
            entity_name = entity.name or entity.display_name
            entity_ror = entity.ror
            entity_country_code = entity.country_code or entity.country
            entity_type = entity.type
        else:
            entity_id = None

        aff_data_create = AffiliationCreate(
            research_item_id=research_item_id,
            research_item_external_id=research_item_data.get("external_id", ""),
            research_item_doi=research_item_data.get("doi"),
            research_item_title=research_item_data.get("title"),
            research_item_year=research_item_data.get("year"),
            research_item_source=research_item_data.get("source_name"),
            author_external_id=author_external_id,
            author_full_name=author_full_name,
            author_orcid=author_orcid,
            entity_id=entity_id,
            entity_name=entity_name,
            entity_external_id=entity_external_id,
            entity_ror=entity_ror,
            entity_country_code=entity_country_code,
            entity_type=entity_type,
            role=role,
            raw_affiliation_data=aff_data,
        )
        return self.affiliation_service.create(self.session, aff_data_create)

    def process_research_item(self, research_item_id: int):
        """Process a single research item and create affiliations"""
        item = self.session.exec(
            select(ResearchItem).where(ResearchItem.id == research_item_id)
        ).first()

        if not item:
            return 0

        source_name = self.get_source_name(item.source_id)

        research_item_data = {
            "external_id": item.external_id,
            "doi": item.doi,
            "title": item.title,
            "year": item.year,
            "source_name": source_name,
        }

        metrics = item.metrics or {}
        authors_data = metrics.get("authors", [])

        created_count = 0

        for idx, author_data in enumerate(authors_data):
            author_external_id = author_data.get("author_id")
            if not author_external_id:
                continue

            author_full_name = author_data.get("display_name")
            author_orcid = author_data.get("orcid")

            role = None
            if author_data.get("roles"):
                role = author_data["roles"][0] if author_data["roles"] else None

            affiliations = author_data.get("affiliations", [])
            if not affiliations:
                self.create_affiliation(
                    author_external_id,
                    item.id,
                    research_item_data,
                    author_full_name,
                    author_orcid,
                    {},
                    role,
                )
                created_count += 1
                continue

            for aff in affiliations:
                self.create_affiliation(
                    author_external_id,
                    item.id,
                    research_item_data,
                    author_full_name,
                    author_orcid,
                    aff,
                    role,
                )
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
