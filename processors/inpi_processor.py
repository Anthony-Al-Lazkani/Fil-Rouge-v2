import re
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


    # Liste des marqueurs d'organisations
    ORG_MARKERS = [
        "CORP", "CORPORATION", "UNIV", "UNIVERSITY", "TECHNOLOGY", "INSTITUTE", 
        "LTD", "INC", "LLC", "GMBH", "SAS", "SARL", "CO", "SYSTEMS", "LABS", "CITY"
    ]

    def clean_name(self, name: str) -> str:
        name = re.sub(r'\[.*?\]', '', name)
        name = name.replace('-', ' ').replace(',', ' ').replace('.', ' ')
        name = name.upper()
        return " ".join(name.split()).strip()

    def is_probably_human(self, name: str) -> bool:
        """Détermine si le nom est un humain ou une organisation."""
        parts = name.split()
        
        # 1. Si un seul mot (souvent une marque ou une erreur)
        if len(parts) < 2: return False
        
        # 2. Si contient un mot-clé d'entreprise
        if any(marker in name for marker in self.ORG_MARKERS):
            return False
            
        # 3. Si le nom est anormalement long (ex: Taipei City University...)
        if len(name) > 40:
            return False
            
        return True

    def get_or_create_author(self, raw_name: str):
        display_name = self.clean_name(raw_name)
        
        # SI CE N'EST PAS UN HUMAIN, ON SORT
        if not self.is_probably_human(display_name):
            return None 
            
        author_slug = f"person_{display_name.lower().replace(' ', '_')}"
        author = self.session.exec(select(Author).where(Author.external_id == author_slug)).first()
        
        if not author:
            author = Author(full_name=display_name, external_id=author_slug)
            self.session.add(author)
        return author

    def process_patents(self, patents: list) -> int:
        count = 0
        for p in patents:
            ext_id = p["external_id"]
            
            existing = self.session.exec(select(ResearchItem).where(ResearchItem.external_id == ext_id)).first()
            if existing: continue

            try:
                # Création/Récupération des auteurs
                for name in p["authors"]:
                    self.get_or_create_author(name)

                # Création du brevet
                item = ResearchItem(
                    source_id=self.source_id,
                    external_id=ext_id,
                    title=p["title"],
                    abstract=p["abstract"],
                    year=p["year"],
                    type="patent",
                    is_open_access=True,
                    raw=p
                )
                self.session.add(item)
                count += 1
            except Exception as e:
                print(f"Erreur processing brevet {ext_id}: {e}")
                
        self.session.commit()
        return count