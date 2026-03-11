"""
Processeur épuré pour les données HAL.

Features:
- Initialisation de la source HAL.
- Déduplication par external_id et par DOI (inter-sources).
- Création simplifiée des auteurs.
- Insertion directe dans ResearchItem avec stockage complet dans 'raw'.
"""

from sqlmodel import Session, select
from database import engine
from models import ResearchItem, Author, Source

class HalProcessor:
    def __init__(self):
        self.session = Session(engine)
        # Initialisation ou récupération de la source
        source = self.session.exec(select(Source).where(Source.name == "HAL")).first()
        if not source:
            source = Source(name="HAL", type="academic", base_url="https://hal.science/")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source = source

    def get_or_create_author(self, full_name: str):
        """Récupère ou crée l'auteur (clé pivot : nom pour HAL car pas d'ID)."""
        ext_id = f"hal_{full_name.replace(' ', '_').lower()}"
        author = self.session.exec(select(Author).where(Author.external_id == ext_id)).first()
        
        if not author:
            author = Author(full_name=full_name, external_id=ext_id)
            self.session.add(author)
            self.session.commit()
            self.session.refresh(author)
        return author

    def process_records(self, records: list) -> int:
        """Traite et insère les notices HAL."""
        processed_count = 0

        for record in records:
            publication = record.get("publication", {})
            ext_id = publication.get("id")
            doi = publication.get("doi")

            if not ext_id:
                continue

            # 1. Check doublon par external_id (Source HAL)
            existing = self.session.exec(
                select(ResearchItem).where(ResearchItem.external_id == ext_id)
            ).first()
            if existing: continue

            # 2. Check doublon par DOI (Toutes sources confondues)
            if doi:
                existing_doi = self.session.exec(
                    select(ResearchItem).where(ResearchItem.doi == doi)
                ).first()
                if existing_doi: continue

            try:
                # Création des auteurs
                for auth in record.get("authors", []):
                    name = auth.get("display_name")
                    if name:
                        self.get_or_create_author(name)

                # Création du ResearchItem épuré
                item = ResearchItem(
                    source_id=self.source.id,
                    external_id=ext_id,
                    doi=doi,
                    title=publication.get("title"),
                    abstract=None, # HAL ne fournit pas d'abstract dans ce flux
                    year=publication.get("year"),
                    type=publication.get("type", "ART"),
                    language="fr",
                    is_open_access=True,
                    keywords=publication.get("keywords", []),
                    topics=publication.get("domains", []),
                    raw=record  # Crucial pour AffiliationProcessor
                )
                
                self.session.add(item)
                processed_count += 1

                if processed_count % 100 == 0:
                    self.session.commit()

            except Exception as e:
                self.session.rollback()
                print(f"Error processing HAL record {ext_id}: {e}")
                continue

        self.session.commit()
        return processed_count