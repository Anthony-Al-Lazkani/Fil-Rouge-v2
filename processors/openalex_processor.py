from database import get_session
from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from services.author_service import AuthorService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate
from schemas.author import AuthorCreate
from typing import List, Dict, Any


class OpenAlexProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.source_service = SourceService()
        self.item_service = ResearchItemService()
        self.author_service = AuthorService()

        # Create or get OpenAlex source
        self.openalex_source = self.source_service.create(
            self.session,
            SourceCreate(
                name="openalex",
                type="academic",
                base_url="https://openalex.org/",
            ),
        )

    def exists(self, external_id: str) -> bool:
        """Check if an article already exists in the DB"""
        return (
            self.item_service.get_by_external_id(
                self.session, self.openalex_source.id, external_id
            )
            is not None
        )

    def create_authors(self, work_data: Dict[str, Any]) -> List[int]:
        """Create authors in database and return their IDs"""
        author_ids = []

        for author_data in work_data["authors"]:
            author_create = AuthorCreate(
                full_name=author_data.get("display_name")
                or author_data.get("raw_author_name", ""),
                external_id=str(author_data["author_id"])
                if author_data.get("author_id")
                else None,
                orcid=author_data.get("orcid"),
                roles=author_data.get("roles", []),
                affiliations=author_data.get("affiliations", []),
            )
            author = self.author_service.create(self.session, author_create)
            author_ids.append(author.id)

        return author_ids

    def create_research_item(self, work_data: Dict[str, Any], author_ids: List[int]):
        """Create research item in database"""
        research_item = ResearchItemCreate(
            source_id=self.openalex_source.id,
            external_id=work_data["external_id"],
            type=work_data.get("type", "article"),
            doi=work_data.get("doi"),
            title=work_data.get("title"),
            abstract=work_data.get("abstract"),
            year=work_data.get("year"),
            publication_date=work_data.get("publication_date"),
            language=work_data.get("language"),
            is_retracted=work_data.get("is_retracted", False),
            is_open_access=work_data.get("is_open_access", False),
            license=work_data.get("license"),
            url=work_data.get("url"),
            citation_count=work_data.get("citation_count", 0),
            keywords=work_data.get("keywords", []),
            topics=work_data.get("topics", []),
            metrics={
                "author_ids": author_ids,
                "authors": work_data["authors"],
                "open_access_location": work_data.get("open_access_location"),
                "source_name": work_data.get("source_name"),
                "source_issn": work_data.get("source_issn"),
                "source_type": work_data.get("source_type"),
                "version": work_data.get("version"),
                "is_accepted": work_data.get("is_accepted"),
                "is_published": work_data.get("is_published"),
                "referenced_works": work_data.get("referenced_works", []),
                "related_works": work_data.get("related_works", []),
            },
            raw=work_data.get("raw"),
        )
        return self.item_service.create(self.session, research_item)

    def process_works(self, works: List[Dict[str, Any]]) -> int:
        """Process a list of works and insert them into the database"""
        processed_count = 0

        for work_data in works:
            external_id = work_data["external_id"]

            if self.exists(external_id):
                continue  # skip duplicates

            # Create authors
            author_ids = self.create_authors(work_data)

            # Create research item
            self.create_research_item(work_data, author_ids)
            processed_count += 1

        return processed_count
