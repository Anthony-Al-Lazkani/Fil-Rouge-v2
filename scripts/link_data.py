"""
Ce script assure la liaison relationnelle entre les entités de la base de données.

Il parcourt les données brutes (JSON) stockées dans chaque 'ResearchItem' pour :
1. Extraire les noms des auteurs selon les structures spécifiques à chaque source (OpenAlex, HAL, etc.).
2. Faire correspondre ces noms avec les entrées existantes de la table 'Author' (via un matching flexible).
3. Identifier les organisations (Entity) liées à ces auteurs au moment de la publication.
4. Créer les entrées dans la table 'Affiliation', consolidant ainsi le lien Auteur-Article-Organisation.

Ce traitement est crucial pour transformer une base documentaire isolée en un graphe 
de connaissances exploitable pour la recherche et l'analyse ontologique.
"""

import sys, os, re
from sqlmodel import Session, select
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from models import ResearchItem, Author, Affiliation

def run_linker():
    print("=== LIAISON FLEXIBLE : MATCHING PAR NOM ===")
    with Session(engine) as session:
        # 1. On charge tous les auteurs pour comparer en Python (plus rapide que 1000 requêtes SQL)
        all_authors = session.exec(select(Author)).all()
        # On crée un mapping : Nom normalisé -> Slug
        # ex: "CHAUDHARI ARCHANA" -> "person_chaudhari_archana"
        auth_map = {a.full_name.upper().strip(): a.external_id for a in all_authors}

        items = session.exec(select(ResearchItem)).all()
        created = 0

        for item in items:
            raw = item.raw or {}
            raw_names = []

            # Extraction des noms bruts selon tes exemples
            if "authorships" in raw: # OpenAlex
                raw_names = [a.get("author", {}).get("display_name") for a in raw["authorships"]]
            elif "authors" in raw: # ArXiv / Semantic / INPI
                val = raw["authors"]
                if isinstance(val, list):
                    if len(val) > 0 and isinstance(val[0], dict): # Semantic
                        raw_names = [v.get("name") for v in val]
                    else: # ArXiv / INPI
                        raw_names = val
                else: raw_names = [val]
            elif "authFullName_s" in raw: # HAL
                raw_names = raw["authFullName_s"] if isinstance(raw["authFullName_s"], list) else [raw["authFullName_s"]]

            # Nettoyage et Matching (FUZZY-MATCHING)
            for name in filter(None, raw_names):
                name_up = re.sub(r'[^a-zA-Z\s]', ' ', name).upper().strip()
                name_up = " ".join(name_up.split())

                # 1. Tentative de match exact
                target_slug = auth_map.get(name_up)

                # 2. Tentative de match par initiale (ex: D. Martirosyan -> Danik Martirosyan)
                if not target_slug:
                    parts = name_up.split()
                    if len(parts) >= 2:
                        last_name = parts[-1]
                        initial = parts[0][0]
                        # On cherche dans les auteurs si un nom finit par Martirosyan et commence par D
                        for full_n, slug in auth_map.items():
                            f_parts = full_n.split()
                            if len(f_parts) >= 2 and f_parts[-1] == last_name and f_parts[0][0] == initial:
                                target_slug = slug
                                break

                if target_slug:
                    # Vérifier doublon
                    stmt = select(Affiliation).where(
                        Affiliation.research_item_id == item.id,
                        Affiliation.author_external_id == target_slug
                    )
                    if not session.exec(stmt).first():
                        new_aff = Affiliation(
                            research_item_id=item.id,
                            author_external_id=target_slug,
                            source_name="linker_flexible",
                            research_item_doi=item.doi
                        )
                        session.add(new_aff)
                        created += 1

        session.commit()
        print(f"=== TERMINÉ : {created} liens créés. ===")

if __name__ == "__main__":
    run_linker()