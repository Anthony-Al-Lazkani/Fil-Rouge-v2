"""
Script de pull-matching pour les organisations.
Complète les affiliations existantes en reliant les auteurs aux entités (Entity)
via les ROR, les noms alternatifs et les domaines d'emails.
"""

import sys, os, re
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from database import engine
from models import ResearchItem, Entity, Affiliation

def run_org_linker():
    print("=== LIAISON DES ORGANISATIONS (PULL) ===")
    with Session(engine) as session:
        # 1. Mise en cache des entités pour éviter des milliers de requêtes
        all_entities = session.exec(select(Entity)).all()
        
        # Mapping ROR -> ID (Très fiable)
        ror_map = {e.ror: e.id for e in all_entities if e.ror}
        
        # Mapping Noms (Exact + Alternatifs) -> ID
        name_map = {}
        domain_map = {}
        for e in all_entities:
            # Nom principal
            name_map[e.name.upper().strip()] = e.id
            if e.display_name:
                name_map[e.display_name.upper().strip()] = e.id
            
            # Noms alternatifs stockés dans le raw par ton nouveau processeur
            alt_names = e.raw.get("_alt_names", [])
            for alt in alt_names:
                name_map[alt.upper().strip()] = e.id
            
            # Domaine email
            domain = e.raw.get("_email_domain")
            if domain:
                domain_map[domain.lower()] = e.id

        # 2. Récupérer les affiliations qui n'ont pas encore d'entité
        affiliations = session.exec(select(Affiliation).where(Affiliation.entity_id == None)).all()
        updated = 0

        for aff in affiliations:
            # Récupérer l'article associé pour lire ses données brutes
            item = session.get(ResearchItem, aff.research_item_id)
            if not item or not item.raw:
                continue

            raw = item.raw
            target_entity_id = None
            found_ror = None

            # --- LOGIQUE OPENALEX ---
            if "authorships" in raw:
                for auth in raw["authorships"]:
                    # On simplifie le matching auteur pour plus de souplesse
                    for inst in auth.get("institutions", []):
                        ror_val = inst.get("ror") # OpenAlex fournit l'URL complète ici aussi
                        
                        # Match direct par ROR (URL complète contre URL complète)
                        target_entity_id = ror_map.get(ror_val)
                        
                        if target_entity_id:
                            found_ror = ror_val
                            break
                        
                        # Fallback par Nom
                        inst_name = inst.get("display_name", "").upper().strip()
                        target_entity_id = name_map.get(inst_name)
                        
                        if target_entity_id: break
                    if target_entity_id: break

            # --- LOGIQUE DOMAINE EMAIL (Transversal : ArXiv, HAL, OpenAlex) ---
            if not target_entity_id:
                # Chercher un champ email dans le raw (varie selon la source)
                email = raw.get("email") or raw.get("corresponding_author_email")
                if email and "@" in email:
                    domain = email.split("@")[-1].lower()
                    target_entity_id = domain_map.get(domain)

            # --- LOGIQUE HAL (Noms de structures) ---
            if not target_entity_id and "structName_s" in raw:
                structs = raw["structName_s"]
                if isinstance(structs, str): structs = [structs]
                for s_name in structs:
                    target_entity_id = name_map.get(s_name.upper().strip())
                    if target_entity_id: break

            # 3. Mise à jour de l'affiliation
            if target_entity_id:
                aff.entity_id = target_entity_id
                aff.entity_ror = found_ror
                session.add(aff)
                updated += 1

        session.commit()
        print(f"=== TERMINÉ : {updated} affiliations enrichies avec une organisation. ===")

if __name__ == "__main__":
    run_org_linker()