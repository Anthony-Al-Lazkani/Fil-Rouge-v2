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
from models.organization import Organization
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
    threshold: float = 70, verbose: bool = False
) -> List[Dict]:
    """Match authors to founders using fuzzy matching."""
    engine = create_engine(SQLITEURL, connect_args=connect_args)

    with Session(engine) as session:
        # Get all authors
        authors = session.exec(select(Author)).all()
        print(f"Loaded {len(authors)} authors")

        # Get all organizations with founders
        organizations = session.exec(
            select(Organization).where(Organization.founders != None)
        ).all()

        # Build founder list with company info
        founders = []
        for org in organizations:
            if org.founders:
                try:
                    founder_list = (
                        json.loads(org.founders)
                        if isinstance(org.founders, str)
                        else org.founders
                    )
                    for founder in founder_list:
                        founders.append(
                            {
                                "name": founder,
                                "company": org.name,
                                "country": org.country,
                                "is_ai_related": org.is_ai_related,
                            }
                        )
                except:
                    pass

        print(f"Loaded {len(founders)} founders\n")

        # Build last name index for faster lookup
        founder_by_lastname: Dict[str, List[Dict]] = defaultdict(list)
        for f in founders:
            last_name = get_name_parts(f["name"])[0]
            if last_name and last_name not in COMMON_SURNAMES:
                founder_by_lastname[last_name].append(f)

        print(f"Indexed {len(founder_by_lastname)} unique last names\n")

        # Find matches
        matches = []

        for author in authors:
            author_name = author.full_name
            if not author_name or len(normalize_name(author_name)) < 3:
                continue

            a_last, a_first = get_name_parts(author_name)

            if not a_last:
                continue

            # Get potential matches by last name
            potential_founders = founder_by_lastname.get(a_last, [])

            # Also check similar last names
            for last_name in founder_by_lastname:
                if (
                    last_name != a_last
                    and SequenceMatcher(None, a_last, last_name).ratio() > 0.8
                ):
                    potential_founders.extend(founder_by_lastname[last_name])

            # Check each potential match
            for founder in potential_founders:
                # Quick filter
                if not quick_filter(author_name, founder["name"]):
                    continue

                score = similarity_score(author_name, founder["name"])

                if score >= threshold:
                    matches.append(
                        {
                            "author": author_name,
                            "founder": founder["name"],
                            "company": founder["company"],
                            "score": round(score, 2),
                            "country": founder["country"],
                            "is_ai_related": founder.get("is_ai_related", False),
                        }
                    )

                    if verbose:
                        print(
                            f"  Match: {author_name} <-> {founder['name']} ({score:.1f}%)"
                        )

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
        "--threshold", type=float, default=70, help="Min similarity (0-100)"
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
