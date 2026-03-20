"""
Ce script utilise la bibliothèque 'pyalex' pour interroger l'index mondial OpenAlex. 
Il se concentre sur l'extraction de travaux (Works) associés au concept 'Artificial Intelligence'.

Variables de contrôle (Pilotables via le pipeline) :
- max_articles : Nombre total d'articles à récupérer sur l'ensemble de la période.
- from_year : Année de départ pour la collecte.
- per_page : Taille des lots demandés à l'API (max 100).

Fonctionnement :
Le script boucle sur les années demandées, applique un filtre par concept (C41008148) 
et récupère les métadonnées enrichies (DOI, Abstracts, Citations, Keywords, Topics).

Limitations:
- présence inégale de DOI
"""


from pyalex import Works, config
from typing import List, Dict, Any
import time

# ------------------ CONFIG ------------------
config.email = "anthonylazkani.22@gmail.com"
config.max_retries = 3

AI_CONCEPT_ID = "C41008148" #recherche lié à l'IA
START_YEAR = 2026
END_YEAR = 2026
PER_PAGE = 100


# ------------------ MAIN CRAWLING FUNCTION ------------------

"""
Logique technique :
    1. Itère sur la plage d'années définie (from_year à to_year).
    2. Initialise une requête filtrée sur le concept IA (C41008148) avec tri chronologique descendant.
    3. Utilise un paginateur pour parcourir les résultats par lots (PER_PAGE).
    4. Extrait et normalise les 'authorships' pour isoler les rôles (first, corresponding) et les affiliations (ROR, pays).
    5. Capture les métadonnées de diffusion : DOI, Open Access, licences et sources (ISSN).
    6. Récupère les relations sémantiques : mots-clés, thématiques (topics) et citations (referenced_works).
"""

def crawl_openalex_ai(max_articles: int = 10, from_year: int = START_YEAR, to_year: int = END_YEAR) -> List[Dict[str, Any]]:
    """
    Récupère les publications OpenAlex.
    """
    all_works = []

    for year in range(from_year, to_year + 1): # 1.
        print(f"\n=== Crawling year {year} ===")

        if len(all_works) >= max_articles:
            break

        query = (
            Works()
            .filter(concepts={"id": AI_CONCEPT_ID}, publication_year=year) # 2.
            .sort(publication_date="desc")
        )

        pager = query.paginate(per_page=PER_PAGE) # 3.

        for page in pager:
            if len(all_works) >= max_articles:
                break

            for work in page:
                if len(all_works) >= max_articles:
                    break
                
                external_id = work.get("id")
                title = work.get("title")
                doi = work.get("doi")

                # Skip deprecated works
                if title is None or title.lower() == "deprecated":
                    continue

                # Extract authors with full details 4.
                authors = []
                for idx, auth in enumerate(work.get("authorships", [])):
                    a = auth.get("author", {})
                    author_affiliations = []
                    for inst in auth.get("institutions", []):
                        author_affiliations.append(
                            {
                                "id": inst.get("id"),
                                "display_name": inst.get("display_name"),
                                "ror": inst.get("ror"),
                                "country_code": inst.get("country_code"),
                                "type": inst.get("type"),
                            }
                        )

                    roles = []
                    if auth.get("is_corresponding"):
                        roles.append("corresponding_author")
                    if idx == 0:
                        roles.append("first_author")
                    if not roles:
                        roles.append("co_author")

                    author_data = {
                        "author_id": a.get("id"),
                        "display_name": a.get("display_name"),
                        "orcid": a.get("orcid"),
                        "raw_author_name": auth.get("raw_author_name"),
                        "roles": roles,
                        "affiliations": author_affiliations,
                        "countries": auth.get("countries", []),
                    }
                    authors.append(author_data)

                # Extract location info
                loc = work.get("primary_location") or {}
                source_info = loc.get("source") or {}

                # Build work data structure - 5. + 6.
                work_data = {
                    "external_id": external_id,
                    "type": work.get("type", "article"),
                    "doi": work.get("doi"),
                    "title": title,
                    "abstract": work.get("abstract"),
                    "year": work.get("publication_year"),
                    "publication_date": work.get("publication_date"),
                    "language": work.get("language"),
                    "is_retracted": work.get("is_retracted", False),
                    "is_open_access": loc.get("is_oa", False),
                    "license": loc.get("license"),
                    "url": loc.get("landing_page_url"),
                    "citation_count": work.get("cited_by_count", 0),
                    "keywords": [
                        kw.get("display_name") for kw in work.get("keywords", [])
                    ]
                    if work.get("keywords")
                    else [],
                    "topics": [t.get("display_name") for t in work.get("topics", [])]
                    if work.get("topics")
                    else [],
                    "authors": authors,
                    "open_access_location": loc.get("landing_page_url"),
                    "source_name": source_info.get("display_name"),
                    "source_issn": source_info.get("issn"),
                    "source_type": source_info.get("type"),
                    "version": loc.get("version"),
                    "is_accepted": loc.get("is_accepted"),
                    "is_published": loc.get("is_published"),
                    "referenced_works": work.get("referenced_works", [])[
                        :10
                    ],  # Limit to first 10
                    "related_works": work.get("related_works", [])[:5],
                    "raw": work,
                }

                all_works.append(work_data)

                if len(all_works) % 100 == 0:
                    print(f"Collected {len(all_works)} articles...", end="\r")

                # Optional: small pause to be polite
                time.sleep(0.01)

    print(f"\nDone. Collected {len(all_works)} clean articles.")
    return all_works


if __name__ == "__main__":
    crawl_openalex_ai()