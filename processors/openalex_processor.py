"""
Processeur d'ingestion pour les publications OpenAlex.
Synchronisé avec le crawler pyalex personnalisé.
"""

from sqlmodel import Session, select
from models import ResearchItem, Author, Source

class OpenAlexProcessor:
    def __init__(self, session: Session):
        self.session = session
        # Initialisation ou récupération de la source
        source = self.session.exec(select(Source).where(Source.name == "openalex")).first()
        if not source:
            source = Source(name="openalex", type="academic", base_url="https://openalex.org/")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    def get_or_create_author(self, author_data: dict):
        """Récupère l'auteur via l'ID OpenAlex (ex: https://openalex.org/A50...)"""
        full_ext_id = author_data.get("author_id")
        if not full_ext_id: return None
        
        # On garde l'ID propre
        ext_id = str(full_ext_id).replace("https://openalex.org/", "")
        
        author = self.session.exec(
            select(Author).where(Author.external_id == ext_id)
        ).first()
        
        if not author:
            # On utilise le display_name extrait par ton crawler
            author = Author(
                full_name=author_data.get("display_name") or "Unknown Author",
                external_id=ext_id,
                orcid=author_data.get("orcid")
            )
            self.session.add(author)
        return author

    def process_works(self, works: list) -> int:
        """Traite les dictionnaires générés par crawl_openalex_ai()"""
        processed_count = 0

        for w in works:
            ext_id = w.get("external_id")
            raw_doi = w.get("doi")
            
            # NORMALISATION DU DOI
            # On retire le préfixe URL pour ne garder que le 10.xxxx
            doi = None
            if raw_doi:
                doi = str(raw_doi).replace("https://doi.org/", "").strip()

            if not ext_id: continue

            # 1. Vérification doublon par DOI (Maintenant ils seront identiques !)
            existing = None
            if doi:
                existing = self.session.exec(
                    select(ResearchItem).where(ResearchItem.doi == doi)
                ).first()
            
            # 2. Déduplication ID
            if not existing:
                existing = self.session.exec(select(ResearchItem).where(ResearchItem.external_id == ext_id)).first()

            if existing: continue

            try:
                # Création des auteurs via la liste 'authors' de ton crawler
                for auth_data in w.get("authors", []):
                    self.get_or_create_author(auth_data)

                # Création du ResearchItem avec tes champs mappés
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
                    # On garde le 'raw' complet (l'objet 'work' original de pyalex)
                    raw=w.get("raw") 
                )
                
                self.session.add(item)
                processed_count += 1

            except Exception as e:
                print(f"Error processing OpenAlex work {ext_id}: {e}")
                continue

        self.session.commit()
        return processed_count