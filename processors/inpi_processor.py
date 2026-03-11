"""
Processeur pour les brevets INPI / EPO.
Traite les brevets comme des ResearchItem de type 'patent'.
"""
from sqlmodel import Session, select
from models import ResearchItem, Author, Source

class InpiProcessor:
    def __init__(self, session: Session):
        self.session = session
        source = self.session.exec(select(Source).where(Source.name == "epo_ops")).first()
        if not source:
            source = Source(name="epo_ops", type="patent", base_url="https://ops.epo.org/")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    def get_or_create_author(self, name: str, patent_id: str, idx: int):
        ext_id = f"epo_{patent_id}_{idx}"
        author = self.session.exec(select(Author).where(Author.external_id == ext_id)).first()
        if not author:
            author = Author(full_name=name, external_id=ext_id)
            self.session.add(author)
        return author

    def process_patents(self, patents: list) -> int:
        count = 0
        for p in patents:
            ext_id = p["external_id"]
            
            # Déduplication
            existing = self.session.exec(select(ResearchItem).where(ResearchItem.external_id == ext_id)).first()
            if existing: continue

            try:
                # Création des auteurs (inventeurs et déposants)
                for idx, name in enumerate(p["authors"]):
                    self.get_or_create_author(name, ext_id, idx)

                # Création du brevet
                item = ResearchItem(
                    source_id=self.source_id,
                    external_id=ext_id,
                    title=p["title"],
                    abstract=p["abstract"],
                    year=p["year"],
                    type="patent", # Voilà ton type spécifique
                    is_open_access=True, # Un brevet est public par définition
                    raw=p
                )
                self.session.add(item)
                count += 1
            except Exception as e:
                print(f"Erreur processing brevet {ext_id}: {e}")
                
        self.session.commit()
        return count