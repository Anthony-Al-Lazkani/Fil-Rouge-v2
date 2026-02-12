from database import get_session
from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from services.author_service import AuthorService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate
from schemas.author import AuthorCreate
from typing import List, Dict, Any


class HalProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.source_service = SourceService()
        self.item_service = ResearchItemService()
        self.author_service = AuthorService()

        # Create or get HAL source
        self.hal_source = self.source_service.create(
            self.session,
            SourceCreate(
                name="HAL",
                type="academic",
                base_url="https://hal.science/",
            ),
        )

    def exists(self, external_id: str) -> bool:
        """Check if an article already exists in the DB"""
        return (
            self.item_service.get_by_external_id(
                self.session, self.hal_source.id, external_id
            )
            is not None
        )

    def exists_by_doi(self, doi: str) -> bool:
        """Check if an article with this DOI already exists in the DB from any source"""
        if not doi:
            return False
        return self.item_service.get_by_doi(self.session, doi) is not None

    def create_authors(self, record: Dict[str, Any]) -> List[int]:
        """Create authors in database and return their IDs"""
        author_ids = []

        for author in record.get("authors", []):
            # Convert affiliations to expected format [{"display_name": "institution"}]
            affiliations = []
            for aff in author.get("affiliations", []):
                if isinstance(aff, str):
                    affiliations.append({"display_name": aff})
                elif isinstance(aff, dict):
                    affiliations.append({"display_name": aff.get("display_name", "")})

            author_create = AuthorCreate(
                full_name=author.get("display_name", ""),
                external_id=None,  # HAL doesn't provide author IDs
                orcid=None,
                roles=author.get("roles", []),
                affiliations=affiliations,
            )
            db_author = self.author_service.create(self.session, author_create)
            author_ids.append(db_author.id)

        return author_ids

    def create_research_item(self, record: Dict[str, Any], author_ids: List[int]):
        """Create research item in database"""
        publication = record.get("publication", {})
        organizations = record.get("organizations", {})

        research_item = ResearchItemCreate(
            source_id=self.hal_source.id,
            external_id=publication.get("id"),
            doi=publication.get("doi"),
            title=publication.get("title"),
            abstract=None,  # HAL data doesn't include abstract
            year=publication.get("year"),
            type=publication.get("type", "ART"),
            language="fr",  # HAL is primarily French
            is_retracted=False,
            is_open_access=True,  # HAL is open access
            url=None,
            citation_count=0,  # HAL doesn't provide citation counts
            keywords=publication.get("keywords", []),
            topics=publication.get("domains", []),
            metrics={
                "author_ids": author_ids,
                "authors": record.get("authors", []),
                "organizations": organizations,
                "domains": publication.get("domains", []),
                "query": record.get("query"),
            },
            raw=record,
        )
        return self.item_service.create(self.session, research_item)

    def process_records(self, records: List[Dict[str, Any]]) -> int:
        """Process a list of HAL records and insert them into the database"""
        processed_count = 0

        for record in records:
            publication = record.get("publication", {})
            external_id = publication.get("id")
            doi = publication.get("doi")

            if not external_id or self.exists(external_id):
                continue  # skip duplicates

            if self.exists_by_doi(doi):
                continue  # skip records with existing DOIs from other sources

            try:
                # Create authors
                author_ids = self.create_authors(record)

                # Create research item
                self.create_research_item(record, author_ids)
                processed_count += 1
            except Exception as e:
                self.session.rollback()
                print(f"Error processing record {external_id}: {e}")
                continue

        return processed_count

    def load_records_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load HAL records from JSONL file"""
        import json

        records = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception as e:
            print(f"Error loading file {file_path}: {e}")

        return records
