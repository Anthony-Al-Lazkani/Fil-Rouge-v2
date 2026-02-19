from database import get_session
from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from services.author_service import AuthorService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate
from schemas.author import AuthorCreate
from typing import List, Dict, Any


class ArxivProcessor:
    def __init__(self):
        self.session = next(get_session())
        self.source_service = SourceService()
        self.item_service = ResearchItemService()
        self.author_service = AuthorService()

        # Create/get source for ArXiv
        self.arxiv_source = self.source_service.create(
            self.session,
            SourceCreate(name="arxiv", type="academic", base_url="https://arxiv.org/"),
        )

    def exists(self, external_id: str) -> bool:
        """Check if an article already exists in the DB"""
        return (
            self.item_service.get_by_external_id(
                self.session, self.arxiv_source.id, external_id
            )
            is not None
        )

    def create_authors(self, article: Dict[str, Any]) -> List[int]:
        """Create authors in database and return their IDs"""
        author_ids = []
        for author_name in article["authors"]:
            author_create = AuthorCreate(
                full_name=author_name,
                external_id=f"arxiv_{author_name.replace(' ', '_')}",
                roles=["co_author"]
                if author_name != article["authors"][0]
                else ["first_author"],
            )
            author = self.author_service.create(self.session, author_create)
            author_ids.append(author.id)
        return author_ids

    def create_research_item(self, article: Dict[str, Any], author_ids: List[int]):
        """Create research item in database"""
        research_item = ResearchItemCreate(
            source_id=self.arxiv_source.id,
            external_id=article["id"],
            type="article",
            title=article["title"],
            abstract=article.get("summary"),
            year=int(article["published"][:4]),
            is_retracted=False,
            is_open_access=True,
            metrics={
                "author_ids": author_ids,
                "authors": article["authors"],
                "summary": article["summary"],
                "category": article["category"],
                "published": article["published"],
            },
            raw=article,
        )
        return self.item_service.create(self.session, research_item)

    def process_articles(self, articles: List[Dict[str, Any]]) -> int:
        """Process a list of articles and insert them into the database"""
        processed_count = 0

        for article in articles:
            ext_id = article["id"]

            if self.exists(ext_id):
                continue  # skip duplicates

            # Create authors
            author_ids = self.create_authors(article)

            # Create research item
            self.create_research_item(article, author_ids)
            processed_count += 1

        return processed_count
