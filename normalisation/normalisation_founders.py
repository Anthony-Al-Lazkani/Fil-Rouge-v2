#!/usr/bin/env python3
"""
Matching script to find authors who became startup founders.
Uses multiple matching algorithms: exact, fuzzy, Levenshtein, Jaro-Winkler.

Usage:
    python scripts/match_authors_to_founders.py
    python scripts/match_authors_to_founders.py --threshold 85
    python scripts/match_authors_to_founders.py --algorithm exact
"""

import argparse
import sys
from pathlib import Path
from collections import defaultdict
from typing import Optional, Set, Dict, List
from functools import lru_cache

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from difflib import SequenceMatcher
from sqlmodel import Session, create_engine, select

from database.initialize import SQLITEURL, connect_args
from models.author import Author
from models.entity import Entity
from models.affiliation import Affiliation
import json


# Common surnames to skip (too generic)
COMMON_SURNAMES: Set[str] = {
    "smith",
    "jones",
    "wilson",
    "martin",
    "taylor",
    "brown",
    "white",
    "thompson",
    "walker",
    "hall",
    "allen",
    "young",
    "king",
    "wright",
    "scott",
    "green",
    "adams",
    "baker",
    "nelson",
    "carter",
    "mitchell",
    "roberts",
    "chen",
    "wang",
    "li",
    "zhang",
    "liu",
    "yang",
    "huang",
    "kumar",
    "singh",
    "khan",
    "gupta",
    "sharma",
    "jain",
    "patel",
    "sato",
    "suzuki",
    "takahashi",
    "tanaka",
    "watanabe",
    "yamamoto",
    "kim",
    "lee",
    "park",
    "choi",
    "jung",
    "kang",
    "huang",
    "müller",
    "schmidt",
    "schneider",
    "fischer",
    "weber",
    "meyer",
    "rossi",
    "romano",
    "ferrari",
    "esposito",
    "bianchi",
    "ricci",
    "dubois",
    "martin",
    "bernard",
    "thomas",
    "petit",
    "robert",
}


@lru_cache(maxsize=10000)
def normalize_name(name: str) -> str:
    """Normalize name for comparison (cached)."""
    if not name:
        return ""
    name = name.lower().strip()
    titles = ["dr.", "dr", "prof.", "prof", "mr.", "mr", "mrs.", "mrs", "ms.", "ms"]
    for title in titles:
        name = name.replace(title, "")
    name = " ".join(name.split())
    return name.strip()


def get_name_parts(name: str) -> tuple:
    """Extract last name and first name for quick comparison."""
    normalized = normalize_name(name)
    parts = normalized.split()
    if len(parts) == 0:
        return ("", "")
    elif len(parts) == 1:
        return (parts[0], parts[0])
    return (parts[-1], parts[0])  # (last_name, first_name)


def quick_filter(author_name: str, founder_name: str) -> bool:
    """Quick pre-filter to skip obviously different names."""
    a_last, a_first = get_name_parts(author_name)
    f_last, f_first = get_name_parts(founder_name)

    # Skip if too short
    if len(a_last) < 3 or len(f_last) < 3:
        return False

    # Skip common surnames (too generic)
    if a_last in COMMON_SURNAMES or f_last in COMMON_SURNAMES:
        # Only match if first names also match exactly
        if a_first != f_first:
            return False

    # Quick check: last names must be somewhat similar
    a_last_lower = a_last.lower()
    f_last_lower = f_last.lower()

    # Exact match on last name
    if a_last_lower == f_last_lower:
        return True

    # Must share at least 60% of characters
    if len(a_last_lower) > 0 and len(f_last_lower) > 0:
        ratio = SequenceMatcher(None, a_last_lower, f_last_lower).ratio()
        if ratio < 0.6:
            return False

    return True


def similarity_score(name1: str, name2: str) -> float:
    """Calculate similarity score between two names (0-100)."""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    if not n1 or not n2:
        return 0

    # Exact match
    if n1 == n2:
        return 100

    # Sequence matcher (fast)
    return SequenceMatcher(None, n1, n2).ratio() * 100


def match_authors_to_founders(
    threshold: float = 90, verbose: bool = False
) -> List[Dict]:
    """Match authors to founders using fuzzy matching."""
    engine = create_engine(SQLITEURL, connect_args=connect_args)

    with Session(engine) as session:
        # Get all authors
        authors = session.exec(select(Author)).all()
        print(f"Loaded {len(authors)} authors")

        # 1. On charge toutes les entités (pas de filtre .where(Entity.founders) qui plante)
        entities = session.exec(select(Entity)).all()

        # --- BLOC 1 : CRUNCHBASE
        # Build founder list with company info
        founders = []
        for entity in entities:
            raw_data = entity.raw or {}
            # Crunchbase stocke dans 'row' -> 'Founders'
            row = raw_data.get("row", {})
            founders_str = row.get("Founders") 

            if founders_str and isinstance(founders_str, str):
                # On sépare par point-virgule : "Dario Amodei; Jack Clark" -> ["Dario Amodei", "Jack Clark"]
                founder_list = [f.strip() for f in founders_str.split(";") if f.strip()]
                
                for f_name in founder_list:
                    founders.append({
                        "name": f_name,
                        "company": entity.name,
                        "country": entity.country_code,
                        "is_ai_related": getattr(entity, "is_ai_related", False),
                    })


            # --- BLOC 2 : SCANR (avec les leaders) ---
            leaders = raw_data.get("leaders")
            if leaders and isinstance(leaders, list):
                for leader in leaders:
                    # ScanR structure souvent ainsi : {'firstName': 'Jean', 'lastName': 'Dupont'}
                    first = leader.get("firstName", "").strip()
                    last = leader.get("lastName", "").strip()
                    f_name = f"{first} {last}".strip()
                    
                    if len(f_name) > 3:
                        founders.append({
                            "name": f_name,
                            "company": entity.name,
                            "country": entity.country_code,
                            "is_ai_related": getattr(entity, "is_ai_related", False),
                        })

        print(f"Loaded {len(founders)} founders\n")

        # Build last name index for faster lookup
        founder_by_lastname: Dict[str, List[Dict]] = defaultdict(list)
        for f in founders:
            last_name = get_name_parts(f["name"])[0]
            if last_name and last_name not in COMMON_SURNAMES:
                founder_by_lastname[last_name].append(f)

        print(f"Indexed {len(founder_by_lastname)} unique last names\n")

        matches = []
        session.autoflush = False 

        print(f"Starting matching for {len(authors)} authors...")

        for author in authors:
            author_name = author.full_name
            if not author_name: continue

            a_last, a_first = get_name_parts(author_name)
            if not a_last: continue

            # 1. On ne récupère QUE les fondateurs ayant EXACTEMENT le même nom de famille
            # C'est un accès dictionnaire O(1), quasi instantané.
            potential_founders = founder_by_lastname.get(a_last, [])

            for founder in potential_founders:
                # 2. On affine avec le prénom ou le score global
                score = similarity_score(author_name, founder["name"])
                
                if score >= threshold:
                    # On récupère l'ID de l'entité (cache cette requête si possible, ou fais-le à la fin)
                    target_entity = session.exec(
                        select(Entity).where(Entity.name == founder["company"])
                    ).first()
                    
                    if target_entity:
                    # 1. ON GARDE : Enregistrement en base de données
                        new_link = Affiliation(
                            author_external_id=author.external_id,
                            entity_id=target_entity.id,
                            role="founder",
                            source_name=f"match_crunchbase_{int(score)}"
                        )
                        session.add(new_link)
                    
                    # 2. ON MODIFIE : Envoi du dictionnaire complet pour l'affichage final
                    matches.append({
                        "author": author_name,
                        "founder": founder["name"],
                        "company": founder["company"],
                        "score": round(score, 2), # C'est cette clé qui manquait !
                        "country": founder.get("country"),
                        "is_ai_related": founder.get("is_ai_related", False),
                    })

        print("Finalizing database changes...")
        session.commit()
        return matches


def print_matches(matches: List[Dict], limit: Optional[int] = None):
    """Print matches in a nice format."""
    if not matches:
        print("\nNo matches found!")
        return

    # Sort by score descending
    matches = sorted(matches, key=lambda x: x["score"], reverse=True)

    if limit:
        matches = matches[:limit]

    print(f"\n{'=' * 80}")
    print(f"FOUND {len(matches)} MATCHES")
    print(f"{'=' * 80}\n")

    for i, m in enumerate(matches, 1):
        ai_tag = " [AI]" if m.get("is_ai_related") else ""
        print(f"{i}. Author: {m['author']}")
        print(f"   Founder: {m['founder']}")
        print(f"   Company: {m['company']}{ai_tag}")
        print(f"   Country: {m.get('country', 'N/A')}")
        print(f"   Score: {m['score']}%")
        print()

    # Summary by company
    companies = defaultdict(list)
    for m in matches:
        companies[m["company"]].append(m)

    print(f"\n{'=' * 80}")
    print("TOP COMPANIES WITH RESEARCHER FOUNDERS")
    print(f"{'=' * 80}\n")

    sorted_companies = sorted(companies.items(), key=lambda x: len(x[1]), reverse=True)
    for company, co_matches in sorted_companies[:10]:
        print(f"  {company}: {len(co_matches)} founder(s)")


def main():
    parser = argparse.ArgumentParser(description="Match authors to startup founders")
    parser.add_argument(
        "--threshold", type=float, default=80, help="Min similarity (0-100)"
    )
    parser.add_argument("--verbose", action="store_true", help="Print details")
    parser.add_argument("--limit", type=int, default=None, help="Limit results")

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print(f"AUTHOR TO FOUNDER MATCHING (threshold: {args.threshold}%)")
    print("=" * 80 + "\n")

    matches = match_authors_to_founders(threshold=args.threshold, verbose=args.verbose)
    print_matches(matches, limit=args.limit)


if __name__ == "__main__":
    main()
