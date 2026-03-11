"""
Processeur d'ingestion pour les publications OpenAlex.

Features:
- Identification unique par DOI (pivot inter-sources) et external_id.
- Création simplifiée des auteurs (déduplication par identifiant OpenAlex).
- Stockage intégral des métadonnées dans le champ 'raw' pour l'extraction du graphe.
- Insertion directe via SQLModel pour maximiser les performances.
"""

from sqlmodel import Session, select
from database import engine
from models import ResearchItem, Author, Source

class OpenAlexProcessor:
    def __init__(self):
        self.session = Session(engine)
        # Initialisation ou récupération de la source
        source = self.session.exec(select(Source).where(Source.name == "openalex")).first()
        if not source:
            source = Source(name="openalex", type="academic", base_url="https://openalex.org/")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    def get_or_create_author(self, author_data: dict):
        """Gère l'existence de l'auteur via son ID OpenAlex unique."""
        ext_id = author_data.get("author_id")
        if not ext_id: return None
        
        # Nettoyage de l'ID (garde la version courte)
        ext_id = str(ext_id).replace("https://openalex.org/", "")
        
        author = self.session.exec(
            select(Author).where(Author.external_id == ext_id)
        ).first()
        
        if not author:
            author = Author(
                full_name=author_data.get("display_name") or author_data.get("raw_author_name", "Unknown"),
                external_id=ext_id,
                orcid=author_data.get("orcid")
            )
            self.session.add(author)
            self.session.commit()
            self.session.refresh(author)
        return author

    def process_works(self, works: list) -> int:
        """Traite et insère les publications OpenAlex en évitant les doublons."""
        processed_count = 0

        for w in works:
            ext_id = w.get("external_id")
            doi = w.get("doi")
            if not ext_id: continue

            # 1. Vérification doublon par DOI (Toutes sources)
            existing = None
            if doi:
                existing = self.session.exec(select(ResearchItem).where(ResearchItem.doi == doi)).first()
            
            # 2. Vérification par external_id si DOI absent ou non trouvé
            if not existing:
                existing = self.session.exec(select(ResearchItem).where(ResearchItem.external_id == ext_id)).first()

            if existing:
                continue

            # Création des auteurs
            for auth_data in w.get("authors", []):
                self.get_or_create_author(auth_data)

            # Création du ResearchItem (Conforme au modèle épuré)
            item = ResearchItem(
                source_id=self.source_id,
                external_id=ext_id,
                doi=doi,
                title=w.get("title"),
                abstract=w.get("abstract"),
                year=w.get("year"),
                type=w.get("type", "article"),
                is_open_access=w.get("is_open_access", False),
                citation_count=w.get("citation_count", 0),
                keywords=w.get("keywords", []),
                topics=w.get("topics", []),
                raw=w # On garde tout le dictionnaire original ici
            )
            
            self.session.add(item)
            processed_count += 1

            # Commit régulier pour la stabilité
            if processed_count % 100 == 0:
                self.session.commit()

        self.session.commit()
        return processed_count