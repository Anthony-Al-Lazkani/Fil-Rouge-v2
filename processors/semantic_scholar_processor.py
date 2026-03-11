"""
Processeur épuré pour Semantic Scholar.
Harmonisé avec les autres processeurs du pipeline.
"""
from sqlmodel import Session, select
from models import ResearchItem, Author, Source

class SemanticScholarProcessor:
    def __init__(self, session: Session):
        self.session = session
        # Source unique Semantic Scholar
        source = self.session.exec(
            select(Source).where(Source.name == "semantic_scholar")
        ).first()
        if not source:
            source = Source(
                name="semantic_scholar", 
                type="academic", 
                base_url="https://api.semanticscholar.org/"
            )
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    def get_or_create_author(self, author_data: dict):
        """Récupère ou crée l'auteur via son ID S2."""
        s2_id = author_data.get("authorId")
        if not s2_id: return None
        
        ext_id = f"s2_{s2_id}"
        author = self.session.exec(select(Author).where(Author.external_id == ext_id)).first()
        
        if not author:
            author = Author(
                full_name=author_data.get("name", "Unknown"),
                external_id=ext_id
            )
            self.session.add(author)
        return author

    def process_papers(self, papers: list) -> int:
        """Traite et insère les publications Semantic Scholar."""
        count = 0
        for paper in papers:
            ext_id = paper.get("paperId")
            doi = paper.get("externalIds", {}).get("DOI")

            if not ext_id: continue

            # 1. Déduplication par ID Source
            existing = self.session.exec(
                select(ResearchItem).where(ResearchItem.external_id == ext_id)
            ).first()
            if existing: continue

            # 2. Déduplication par DOI (Inter-sources)
            if doi:
                existing_doi = self.session.exec(
                    select(ResearchItem).where(ResearchItem.doi == doi)
                ).first()
                if existing_doi: continue

            try:
                # Création des auteurs
                for auth_data in paper.get("authors", []):
                    self.get_or_create_author(auth_data)


                # Création de l'item
                item = ResearchItem(
                    source_id=self.source_id,
                    external_id=ext_id,
                    doi=doi,
                    title=paper.get("title"),
                    abstract=paper.get("abstract"),
                    year=paper.get("year"),
                    type="article", # Homogénéisation
                    language=None,
                    is_open_access=True if paper.get("openAccessPdf") else False,
                    citation_count=paper.get("citationCount", 0),
                    topics=paper.get("fieldsOfStudy") if paper.get("fieldsOfStudy") else [],
                    raw=paper # Stocke tout le JSON pour AffiliationProcessor
                )
                
                self.session.add(item)
                count += 1

            except Exception as e:
                print(f"Erreur traitement article S2 {ext_id}: {e}")
                continue

        self.session.commit()
        return count