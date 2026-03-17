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
import logging
from difflib import SequenceMatcher
from sqlmodel import Session, select, func
from pathlib import Path
from rapidfuzz import fuzz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from models import ResearchItem, Author, Affiliation

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SOURCE_EXTRACTORS = {
    "openalex": lambda raw: [
        a.get("author", {}).get("display_name") for a in raw.get("authorships", [])
    ],
    "arxiv": lambda raw: raw.get("authors", []),
    "semantic": lambda raw: [v.get("name") for v in raw.get("authors", [])]
    if isinstance(raw.get("authors"), list)
    and len(raw.get("authors", [])) > 0
    and isinstance(raw["authors"][0], dict)
    else [],
    "hal": lambda raw: raw.get("authFullName_s", [])
    if isinstance(raw.get("authFullName_s"), list)
    else [raw.get("authFullName_s")]
    if raw.get("authFullName_s")
    else [],
    "inpi": lambda raw: raw.get("authors", []),
}


def normalize_name(name: str) -> str:
    """Enhanced name normalization with hyphen and middle name handling."""
    if not name:
        return ""
    name = re.sub(r"[^a-zA-Z\s]", " ", name).upper().strip()
    name = " ".join(name.split())
    parts = name.split()
    if len(parts) <= 1:
        return name
    last_name = parts[-1]
    first_parts = [p for p in parts[:-1] if len(p) > 1]
    first_name = first_parts[0] if first_parts else parts[0]
    return f"{first_name} {last_name}"


def extract_author_names(raw: dict) -> list[str]:
    """Extract author names with source detection and metrics."""
    source = raw.get("source", "").lower() if isinstance(raw.get("source"), str) else ""
    names = []

    if "authorships" in raw:
        names = [
            a.get("author", {}).get("display_name") for a in raw.get("authorships", [])
        ]
    elif "authors" in raw:
        val = raw["authors"]
        if isinstance(val, list):
            if len(val) > 0 and isinstance(val[0], dict):
                names = [v.get("name") for v in val]
            else:
                names = val
        else:
            names = [val]
    elif "authFullName_s" in raw:
        names = (
            raw["authFullName_s"]
            if isinstance(raw["authFullName_s"], list)
            else [raw["authFullName_s"]]
        )

    return [n for n in names if n]


def run_linker():
    print("=== LIAISON FLEXIBLE : MATCHING PAR NOM ===")
    stats = {"exact": 0, "initial": 0, "fuzzy": 0, "no_match": 0, "dupes": 0}

    with Session(engine) as session:
        all_authors = session.exec(select(Author)).all()
        auth_map = {a.full_name.upper().strip(): a.external_id for a in all_authors}
        lastname_index = {}
        for full_n, slug in auth_map.items():
            parts = full_n.split()
            if len(parts) >= 2:
                lastname = parts[-1]
                if lastname not in lastname_index:
                    lastname_index[lastname] = []
                lastname_index[lastname].append((full_n, slug))

        items = session.exec(select(ResearchItem)).all()
        created = 0

        for item in items:
            raw = item.raw or {}
            raw_names = extract_author_names(raw)

            for name in raw_names:
                name_normalized = normalize_name(name)
                target_slug = auth_map.get(name_normalized)

                if not target_slug:
                    parts = name_normalized.split()
                    if len(parts) >= 2:
                        last_name = parts[-1]
                        initial = parts[0][0]
                        matches = lastname_index.get(last_name, [])
                        for full_n, slug in matches:
                            f_parts = full_n.split()
                            if f_parts[0][0] == initial:
                                target_slug = slug
                                stats["initial"] += 1
                                break

                if not target_slug and len(name_normalized) > 5:
                    parts = name_normalized.split()
                    if len(parts) >= 2:
                        last_name = parts[-1]
                        matches = lastname_index.get(last_name, [])
                        best_score = 0
                        for full_n, slug in matches:
                            score = fuzz.ratio(name_normalized, full_n)
                            if score > best_score and score >= 85:
                                best_score = score
                                target_slug = slug
                        if target_slug:
                            stats["fuzzy"] += 1

                if target_slug:
                    stmt = select(Affiliation).where(
                        Affiliation.research_item_id == item.id,
                        Affiliation.author_external_id == target_slug,
                    )
                    if not session.exec(stmt).first():
                        new_aff = Affiliation(
                            research_item_id=item.id,
                            author_external_id=target_slug,
                            source_name="linker_flexible",
                            research_item_doi=item.doi,
                            role="author",
                        )
                        session.add(new_aff)
                        created += 1
                    else:
                        stats["dupes"] += 1
                else:
                    stats["no_match"] += 1

        session.commit()
        print(f"=== TERMINÉ : {created} liens créés. ===")
        print(
            f"Stats: exact={stats['exact']}, initial={stats['initial']}, fuzzy={stats['fuzzy']}, no_match={stats['no_match']}, dupes={stats['dupes']}"
        )


def update_author_stats(session: Session):
    """Calcule le nombre réel de publications par auteur via GROUP BY (O(n) au lieu de O(n²))."""
    print("=== MISE À JOUR DES COMPTEURS (PUBLICATION_COUNT) ===")

    stmt = select(
        Affiliation.author_external_id, func.count(Affiliation.id).label("pub_count")
    ).group_by(Affiliation.author_external_id)
    results = session.exec(stmt).all()
    counts = {row[0]: row[1] for row in results}

    authors = session.exec(select(Author)).all()
    updated = 0

    for author in authors:
        count = counts.get(author.external_id, 0)
        if author.publication_count != count:
            author.publication_count = count
            session.add(author)
            updated += 1

    session.commit()
    print(f"=== STATISTIQUES : {updated} auteurs mis à jour. ===")


if __name__ == "__main__":
    # 1. Création des liens (ta fonction run_linker actuelle modifiée)
    run_linker()

    # 2. Mise à jour des compteurs
    with Session(engine) as session:
        update_author_stats(session)
