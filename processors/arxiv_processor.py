"""
Processeur épuré pour les données arXiv.
Harmonisé avec OrganizationProcessor.
"""

from sqlmodel import Session, select
from models import ResearchItem, Author, Source
from datetime import datetime

class ArxivProcessor:
    def __init__(self, session: Session):
        # Utilisation de la session passée en argument pour la cohérence
        self.session = session 
        
        # Récupération ou création de la source unique ArXiv
        source = self.session.exec(select(Source).where(Source.name == "arxiv")).first()
        if not source:
            source = Source(name="arxiv", type="academic", base_url="https://arxiv.org/")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    def get_or_create_author(self, author_name: str):
        """Récupère l'auteur s'il existe déjà, sinon le crée."""
        # On utilise une clé simple basée sur le nom pour l'external_id
        ext_id = f"arxiv_{author_name.replace(' ', '_').lower()}"
        author = self.session.exec(select(Author).where(Author.external_id == ext_id)).first()
        
        if not author:
            author = Author(full_name=author_name, external_id=ext_id)
            self.session.add(author)
            # On ne commit pas ici, on laisse process_articles le faire
        return author

    def process_articles(self, articles: list) -> int:
        """Traite et insère les articles arXiv."""
        count = 0
        for art in articles:
            # 1. Extraction et conversion de la date (Indispensable pour SQLite)
            # On cherche dans "published" (nom standard chez arXiv) ou "publication_date"
            raw_pub_date = art.get("published") or art.get("publication_date")
            clean_date = None

            if raw_pub_date:
                try:
                    # On prend les 10 premiers caractères "YYYY-MM-DD"
                    clean_date = datetime.strptime(raw_pub_date[:10], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    clean_date = None

            # 2. Évite les doublons
            existing = self.session.exec(
                select(ResearchItem).where(ResearchItem.external_id == art["id"])
            ).first()
            if existing: 
                continue

            # 3. Création des auteurs associés
            for name in art.get("authors", []):
                self.get_or_create_author(name)

            # 4. Mapping vers ResearchItem
            item = ResearchItem(
                source_id=self.source_id,
                external_id=art["id"],
                title=art["title"],
                abstract=art.get("summary") or art.get("abstract"),
                year=clean_date.year if clean_date else None,
                publication_date=clean_date, # OBJET DATE ICI (pas de string !)
                type="article",
                is_open_access=True,
                raw=art 
            )
            
            self.session.add(item)
            count += 1

        self.session.commit()
        return count