"""
Processeur épuré pour les données arXiv.

Features:
- Initialisation directe de la source.
- Création/Récupération des auteurs (Upsert sur external_id).
- Insertion de ResearchItem en utilisant uniquement les champs valides.
- Tout le reste est stocké dans le champ 'raw'.
"""

from sqlmodel import Session, select
from database import engine
from models import ResearchItem, Author, Source

class ArxivProcessor:
    def __init__(self):
        self.session = Session(engine)
        # On récupère ou crée la source directement
        source = self.session.exec(select(Source).where(Source.name == "arxiv")).first()
        if not source:
            source = Source(name="arxiv", type="academic", base_url="https://arxiv.org/")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source = source

    def get_or_create_author(self, author_name: str):
        """Récupère l'auteur s'il existe déjà, sinon le crée."""
        ext_id = f"arxiv_{author_name.replace(' ', '_').lower()}"
        author = self.session.exec(select(Author).where(Author.external_id == ext_id)).first()
        
        if not author:
            author = Author(full_name=author_name, external_id=ext_id)
            self.session.add(author)
            self.session.commit()
            self.session.refresh(author)
        return author

    def process_articles(self, articles: list) -> int:
        """Traite et insère les articles arXiv."""
        processed_count = 0

        for art in articles:
            # Check si l'article existe déjà par son external_id
            existing = self.session.exec(
                select(ResearchItem).where(ResearchItem.external_id == art["id"])
            ).first()
            
            if existing:
                continue

            # On crée les auteurs (utile pour ton graphe plus tard)
            for name in art.get("authors", []):
                self.get_or_create_author(name)

            # Création du ResearchItem (Conforme au nouveau modèle épuré)
            item = ResearchItem(
                source_id=self.source.id,
                external_id=art["id"],
                title=art["title"],
                abstract=art.get("summary"),
                year=int(art["published"][:4]) if art.get("published") else None,
                type="article",
                is_open_access=True,
                raw=art  # C'est ici qu'on met TOUT pour l'AffiliationProcessor
            )
            
            self.session.add(item)
            processed_count += 1

        self.session.commit()
        return processed_count