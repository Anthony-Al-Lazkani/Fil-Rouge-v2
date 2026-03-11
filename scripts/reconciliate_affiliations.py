import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from database import engine
from models import ResearchItem, Entity, Affiliation

import sys, os
from sqlmodel import Session, select
from database import engine
from models import ResearchItem, Entity, Affiliation

def repair_affiliations():
    print("=== RÉCONCILIATION DES LIENS AUTEURS / LABOS ===")
    with Session(engine) as session:
        # On récupère tous les articles qui ont des données brutes
        items = session.exec(select(ResearchItem)).all()
        
        count = 0
        for item in items:
            raw = item.raw or {}
            # Pour OpenAlex, les labos sont dans 'authorships'
            authorships = raw.get("authorships", [])
            
            for auth in authorships:
                author_id = auth.get("author", {}).get("id")
                institutions = auth.get("institutions", [])
                
                for inst in institutions:
                    inst_name = inst.get("display_name")
                    ror = inst.get("ror")
                    
                    # On cherche le labo/entité dans ta table Entity
                    # Priorité au ROR, sinon par le nom
                    entity = None
                    if ror:
                        entity = session.exec(select(Entity).where(Entity.external_id == ror)).first()
                    if not entity and inst_name:
                        entity = session.exec(select(Entity).where(Entity.name == inst_name)).first()
                    
                    if entity:
                        # On crée l'affiliation
                        new_aff = Affiliation(
                            research_item_id=item.id,
                            entity_id=entity.id,
                            author_external_id=str(author_id),
                            entity_ror=ror,
                            source_name="repair_script"
                        )
                        session.add(new_aff)
                        count += 1
        
        session.commit()
        print(f"=== SUCCÈS : {count} affiliations créées. ===")

if __name__ == "__main__":
    repair_affiliations()