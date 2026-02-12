from database import get_session
from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from services.author_service import AuthorService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate
from schemas.author import AuthorCreate
from typing import List, Dict, Any


class SemanticScholarProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.source_service = SourceService()
        self.item_service = ResearchItemService()
        self.author_service = AuthorService()

        # Create or get Semantic Scholar source
        self.semantic_scholar_source = self.source_service.create(
            self.session,
            SourceCreate(
                name="semantic_scholar",
                type="academic",
                base_url="https://api.semanticscholar.org/",
            ),
        )

    def exists(self, external_id: str) -> bool:
        """Check if an article already exists in the DB"""
        return (
            self.item_service.get_by_external_id(
                self.session, self.semantic_scholar_source.id, external_id
            )
            is not None
        )

    def create_authors(self, record: Dict[str, Any]) -> List[int]:
        """Create authors in database and return their IDs"""
        author_ids = []

        for idx, author in enumerate(record.get("authors", [])):
            roles = ["first_author"] if idx == 0 else ["co_author"]

            author_create = AuthorCreate(
                full_name=author.get("name", ""),
                external_id=str(author.get("id")),
                # if author.get("authorId")
                # else None,
                orcid=author.get("orcid"),
                roles=roles,
                affiliations=author.get("affiliations", []),
            )
            db_author = self.author_service.create(self.session, author_create)
            author_ids.append(db_author.id)

        return author_ids

    def create_research_item(self, record: Dict[str, Any], author_ids: List[int]):
        """Create research item in database"""
        publication = record.get("publication", {})

        # Prepare authors data for metrics
        authors_for_db = [
            {
                "author_id": author.get("id"),
                "display_name": author.get("name"),
                "orcid": author.get("orcid"),
                "affiliations": author.get("affiliations", []),
                "roles": ["first_author"] if idx == 0 else ["co_author"],
            }
            for idx, author in enumerate(record.get("authors", []))
        ]

        research_item = ResearchItemCreate(
            source_id=self.semantic_scholar_source.id,
            external_id=publication.get("id"),
            doi=publication.get("doi"),
            title=publication.get("title"),
            abstract=publication.get("abstract"),
            year=publication.get("year"),
            type=publication.get("type", "paper"),
            language=publication.get("language"),
            is_retracted=False,
            is_open_access=publication.get("is_open_access"),
            url=publication.get("url"),
            citation_count=publication.get("citation_count", 0),
            keywords=[],
            topics=record.get("fields_of_study", []),
            metrics={
                "author_ids": author_ids,
                "citation_count": publication.get("citation_count", 0),
                "venue": publication.get("venue"),
                "authors": authors_for_db,
                "url": publication.get("url"),
                "external_ids": publication.get("external_ids", {}),
            },
            raw=record,
        )
        return self.item_service.create(self.session, research_item)

    def process_records(self, records: List[Dict[str, Any]]) -> int:
        """Process a list of Semantic Scholar records and insert them into the database"""
        processed_count = 0

        for record in records:
            publication = record.get("publication", {})
            external_id = publication.get("id")

            if not external_id or self.exists(external_id):
                continue  # skip duplicates

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
