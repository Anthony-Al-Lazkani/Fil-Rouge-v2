import sys, os, re
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from database import engine
from models import ResearchItem, Entity, Affiliation, Author

def run_org_linker():
    # Liste noire pour éviter les faux positifs du "Plein Texte"
    # Ces mots sont souvent présents dans les adresses sans être l'entité visée
    BLACKLIST = {"BENCHMARK", "AI", "LAB", "BUSINESS", "FIGURE", "TRAINING", "IMPACT", "SCIENCE", "LABORATORY", "RESEARCH", "COMPANY", "UNIV", "UNIVERSITY"}

    print("=== LIAISON DES ORGANISATIONS (MODE RÉCUPÉRATION CIBLÉE) ===")
    with Session(engine) as session:
        all_entities = session.exec(select(Entity)).all()
        
        ror_map = {e.ror: e.id for e in all_entities if e.ror}
        name_map = {}
        domain_map = {}
        
        for e in all_entities:
            name_up = e.name.upper().strip()
            # Sécurité : on n'ajoute pas les mots de la blacklist au map de recherche textuelle
            if name_up in BLACKLIST:
                continue
            name_map[name_up] = e.id
            
            # Email domain fallback
            domain = e.raw.get("_email_domain") if e.raw else None
            if domain:
                domain_map[domain.lower()] = e.id

        affiliations = session.exec(select(Affiliation).where(Affiliation.entity_id == None)).all()
        updated = 0

        for aff in affiliations:
            item = session.get(ResearchItem, aff.research_item_id)
            if not item or not item.raw: continue
            
            raw = item.raw
            target_entity_id = None
            found_ror = None

            # 1. LOGIQUE OPENALEX (On assouplit la vérification du nom)
            if "authorships" in raw:
                for auth in raw["authorships"]:
                    # On cherche l'institution de n'importe quel auteur de l'article
                    # C'est ce qui permet de passer de 0 à 180.
                    for inst in auth.get("institutions", []):
                        ror_val = inst.get("ror")
                        target_entity_id = ror_map.get(ror_val)
                        
                        if not target_entity_id:
                            inst_name = inst.get("display_name", "").upper().strip()
                            target_entity_id = name_map.get(inst_name)
                        
                        if target_entity_id:
                            found_ror = ror_val
                            break
                    if target_entity_id: break

            # 2. LOGIQUE EMAIL (Très fiable, même sans match de nom)
            if not target_entity_id:
                email = raw.get("email") or raw.get("corresponding_author_email")
                if email and "@" in email:
                    domain = email.split("@")[-1].lower()
                    target_entity_id = domain_map.get(domain)

            # 3. LOGIQUE HAL
            if not target_entity_id and "structName_s" in raw:
                structs = raw["structName_s"]
                if isinstance(structs, str): structs = [structs]
                for s_name in structs:
                    target_entity_id = name_map.get(s_name.upper().strip())
                    if target_entity_id: break
            
            # 4. LOGIQUE DE DERNIER RECOURS : Recherche textuelle CIBLÉE
            if not target_entity_id:
                # On définit les zones "sûres" du JSON selon la source
                search_zones = []
                
                # Zone OpenAlex / ArXiv (Affiliations brutes)
                if "authorships" in raw:
                    for auth in raw["authorships"]:
                        search_zones.append(str(auth.get("raw_affiliation_string", "")).upper())
                        
                # Zone HAL (Structures)
                if "structName_s" in raw:
                    search_zones.append(str(raw["structName_s"]).upper())

                # On ne cherche QUE dans ces zones, pas dans le résumé (abstract) ou le titre
                combined_zones = " ".join(search_zones)
                
                for name_key, ent_id in name_map.items():
                    # Sécurité : Nom de + de 4 lettres ET présent dans les zones d'affiliation
                    if len(name_key) > 4 and name_key in combined_zones:
                        target_entity_id = ent_id
                        break

            # Application de la modif
            if target_entity_id:
                aff.entity_id = target_entity_id
                aff.entity_ror = found_ror
                session.add(aff)
                updated += 1

        session.commit()
        print(f"=== TERMINÉ : {updated} affiliations enrichies. ===")

if __name__ == "__main__":
    run_org_linker()