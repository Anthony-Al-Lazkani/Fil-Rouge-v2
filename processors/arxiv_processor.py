"""
Processeur épuré pour les données arXiv.
Harmonisé avec OrganizationProcessor.
"""

from sqlmodel import Session, select
from models import ResearchItem, Author, Source

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
            # Évite les doublons
            existing = self.session.exec(
                select(ResearchItem).where(ResearchItem.external_id == art["id"])
            ).first()
            if existing: continue

            # Création des auteurs associés
            for name in art.get("authors", []):
                self.get_or_create_author(name)

            # Mapping vers ton modèle ResearchItem
            item = ResearchItem(
                source_id=self.source_id,
                external_id=art["id"],
                title=art["title"],
                abstract=art.get("summary"),
                year=int(art["published"][:4]) if art.get("published") else None,
                # AJOUT : On stocke la date complète si le champ existe dans ton modèle
                publication_date=art["published"][:10] if art.get("published") else None, 
                type="article",
                is_open_access=True,
                raw=art 
            )
            
            self.session.add(item)
            count += 1

        self.session.commit()
        return count