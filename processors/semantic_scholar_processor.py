"""
Processeur épuré pour Semantic Scholar.

Features:
- Identification de la source Semantic Scholar.
- Création/Récupération des auteurs via l'identifiant S2.
- Déduplication stricte par external_id et DOI.
- Centralisation des données brutes dans le champ 'raw'.
"""

from sqlmodel import Session, select
from database import engine
from models import ResearchItem, Author, Source

class SemanticScholarProcessor:
    def __init__(self):
        self.session = Session(engine)
        # Initialisation ou récupération de la source
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
        """Récupère ou crée l'auteur via son ID Semantic Scholar."""
        ext_id = author_data.get("id")
        if not ext_id: return None
        
        ext_id = f"s2_{ext_id}"
        author = self.session.exec(
            select(Author).where(Author.external_id == ext_id)
        ).first()
        
        if not author:
            author = Author(
                full_name=author_data.get("name", "Unknown"),
                external_id=ext_id
            )
            self.session.add(author)
            self.session.commit()
            self.session.refresh(author)
        return author

    def process_records(self, records: list) -> int:
        """Traite et insère les publications Semantic Scholar."""
        processed_count = 0

        for record in records:
            publication = record.get("publication", {})
            ext_id = publication.get("id")
            doi = publication.get("doi")

            if not ext_id: continue

            # 1. Check doublon par external_id
            existing = self.session.exec(
                select(ResearchItem).where(ResearchItem.external_id == ext_id)
            ).first()
            if existing: continue

            # 2. Check doublon par DOI (inter-sources)
            if doi:
                existing_doi = self.session.exec(
                    select(ResearchItem).where(ResearchItem.doi == doi)
                ).first()
                if existing_doi: continue

            try:
                # Création des auteurs
                for auth_data in record.get("authors", []):
                    self.get_or_create_author(auth_data)

                # Création du ResearchItem épuré
                item = ResearchItem(
                    source_id=self.source_id,
                    external_id=ext_id,
                    doi=doi,
                    title=publication.get("title"),
                    abstract=publication.get("abstract"),
                    year=publication.get("year"),
                    type=publication.get("type", "paper"),
                    language=publication.get("language"),
                    is_open_access=publication.get("is_open_access", False),
                    citation_count=publication.get("citation_count", 0),
                    topics=record.get("fields_of_study", []),
                    raw=record # Contient les auteurs et leurs affiliations brutes
                )
                
                self.session.add(item)
                processed_count += 1

                if processed_count % 100 == 0:
                    self.session.commit()

            except Exception as e:
                self.session.rollback()
                print(f"Error processing S2 record {ext_id}: {e}")
                continue

        self.session.commit()
        return processed_count