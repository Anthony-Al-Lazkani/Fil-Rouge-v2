"""
Processeur épuré pour les données HAL.

Features:
- Initialisation de la source HAL.
- Déduplication par external_id et par DOI (inter-sources).
- Création simplifiée des auteurs.
- Insertion directe dans ResearchItem avec stockage complet dans 'raw'.
"""

from sqlmodel import Session, select
from models import ResearchItem, Author, Source

class HalProcessor:
    def __init__(self, session: Session):
        # On utilise la session passée en argument (cohérence pipeline)
        self.session = session
        
        # Initialisation ou récupération de la source
        source = self.session.exec(select(Source).where(Source.name == "HAL")).first()
        if not source:
            source = Source(name="HAL", type="academic", base_url="https://hal.science/")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    def get_or_create_author(self, full_name: str):
        """Récupère ou crée l'auteur."""
        ext_id = f"hal_{full_name.replace(' ', '_').lower()}"
        author = self.session.exec(select(Author).where(Author.external_id == ext_id)).first()
        
        if not author:
            author = Author(full_name=full_name, external_id=ext_id)
            self.session.add(author)
        return author

    def process_records(self, records: list) -> int:
        """Traite et insère les notices HAL (Format API Direct)."""
        processed_count = 0

        for doc in records:
            # Extraction directe des clés HAL
            ext_id = doc.get("halId_s")
            doi = doc.get("doiId_s")

            if not ext_id:
                continue

            # 1. Check doublon par external_id
            existing = self.session.exec(
                select(ResearchItem).where(ResearchItem.external_id == ext_id)
            ).first()
            if existing: continue

            # 2. Check doublon par DOI (Toutes sources)
            if doi:
                existing_doi = self.session.exec(
                    select(ResearchItem).where(ResearchItem.doi == doi)
                ).first()
                if existing_doi: continue

            try:
                # Création des auteurs
                for name in doc.get("authFullName_s", []):
                    self.get_or_create_author(name)

                # Nettoyage du titre
                raw_title = doc.get("title_s")
                title = raw_title[0] if isinstance(raw_title, list) and raw_title else raw_title

                # 3. Logique de mapping du type (À PLACER ICI)
                hal_type = doc.get("docType_s", "ART")
                normalized_type = "article" if hal_type in ["ART", "COUV", "COMM", "POSTER"] else "other"

                # 4. Création du ResearchItem homogénéisé
                item = ResearchItem(
                    source_id=self.source_id,
                    external_id=ext_id,
                    doi=doi,
                    title=title,
                    year=doc.get("producedDateY_i"),
                    type=normalized_type, # Utilisation du type mappé
                    is_open_access=True,
                    keywords=doc.get("keyword_s", []),
                    topics=doc.get("domain_s", []),
                    raw=doc
                )
                
                self.session.add(item)
                processed_count += 1

            except Exception as e:
                print(f"Error processing HAL record {ext_id}: {e}")
                continue

        self.session.commit()
        return processed_count