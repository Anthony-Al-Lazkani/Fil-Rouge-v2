r"""
USAGE:
Commencer par lancer le serveur:
     .\.venv\Scripts\python.exe -m uvicorn main:app --reload

puis python -m crawlers.semantic_scholar_main pour lancer le fichier
    => va générer un fichier 'semantic_scholar_YYYYMMDD_HHMMSS.jsonl' dans Fil-Rouge-v2/data/
    => va enregistrer les lignes dans la database.db

QUERY: Multiple AI-related queries from 2018-2026 / à modifier au besoin

EXPLICATIONS:
    Fonctionne en complément avec semantic_scholar_fetcher.py
    Logique métier + écriture fichier + insertion DB
    Gestion des doublons via IDs existants + try/except en DB

OBSERVATIONS:
    - Utilise l'API Semantic Scholar avec clé API
    - Gère multi-requêtes et multi-années
    - Filtre les doublons avant insertion
    - Multi requêtes obligatoires pour contourner limites d'API Semantic Scholar
"""

# Imports de base pour le crawler => fichier jsonl
import json
import time
from pathlib import Path
from datetime import datetime
from .semantic_scholar_fetcher import SemanticScholarFetcher

# Imports nécessaires pour insertion dans la base de donnée
from database import get_session
from services.research_item_service import ResearchItemService
from services.source_service import SourceService
from schemas.research_item import ResearchItemCreate
from schemas.source import SourceCreate
from sqlalchemy.exc import IntegrityError #ajout de cette ligne pour gérer les erreurs vis-à-vis de l'insertion en DB en cas d'unicité des DOI

# ========== CONFIGURATION ==========
"""QUERIES = [
    "artificial intelligence neural networks",
    "artificial intelligence natural language processing",
    "artificial intelligence computer vision",
    "artificial intelligence reinforcement learning",
    "artificial intelligence robotics",
    "artificial intelligence explainable AI",
    "artificial intelligence generative AI",
    "artificial intelligence machine learning",
]"""
QUERIES = [
    "artificial intelligence",
]
YEARS = list(range(2021, 2026))  # 2018 à 2026
MAX_PER_YEAR = 2500
API_KEY = "BJxxqhUWGI2QmwHvezhLqasQc0I3Sq2e5HrdxnCi"


# ===================================


def load_existing_ids(data_folder="../data"):
    """Charge tous les IDs d'articles déjà crawlés depuis les JSONL"""
    existing_ids = set()
    data_path = Path(__file__).parent.parent / data_folder

    if not data_path.exists():
        print(f"Dossier {data_path} introuvable, création...\n")
        data_path.mkdir(parents=True, exist_ok=True)
        return existing_ids

    jsonl_files = list(data_path.glob("semantic_scholar_*.jsonl"))

    if not jsonl_files:
        print("Aucun fichier précédent trouvé\n")
        return existing_ids

    print(f"Vérification de {len(jsonl_files)} fichier(s) existant(s)...")

    for filepath in jsonl_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        paper_id = record.get("publication", {}).get("id")
                        if paper_id:
                            existing_ids.add(paper_id)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Erreur lecture {filepath}: {e}")

    print(f"{len(existing_ids):,} articles déjà crawlés\n")
    return existing_ids


# ========== INITIALISATION ==========

# Initialisation des services et création de la source Semantic Scholar
source_service = SourceService()
item_service = ResearchItemService()
session = next(get_session())

# Créer ou récupérer la source Semantic Scholar
semantic_scholar = source_service.create(
    session,
    SourceCreate(
        name="semantic_scholar",
        type="academic",
        base_url="https://api.semanticscholar.org/"
    )
)

# Créer le dossier data
data_path = Path(__file__).parent.parent / "data"
'''data_path.mkdir(parents=True, exist_ok=True)'''

# Charger les IDs existants
existing_ids = load_existing_ids()

# Créer le fichier de sortie avec timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = data_path / f"semantic_scholar_{timestamp}.jsonl"

# Initialiser le fetcher
fetcher = SemanticScholarFetcher(api_key=API_KEY, limit=100)

print(f"Fichier de sortie : {output_file}")
print(f"Requêtes : {len(QUERIES)} requêtes")
print(f"Années : {YEARS[0]}-{YEARS[-1]}")

# ========== COMPTEURS GLOBAUX ==========
total_new = 0
total_duplicates = 0
total_fetched = 0
total_db_inserted = 0
total_db_duplicates = 0
start_time = time.time()

# ========== CRAWL PRINCIPAL ==========
with open(output_file, "a", encoding="utf-8") as f:
    for query_idx, query in enumerate(QUERIES, 1):
        print(f"REQUÊTE {query_idx}/{len(QUERIES)}: {query}")

        for year in YEARS:
            print(f"ANNÉE {year}")

            count = 0
            offset = 0
            duplicates_year = 0
            db_inserted_year = 0
            db_duplicates_year = 0
            consecutive_empty = 0

            while count < MAX_PER_YEAR and consecutive_empty < 3:
                try:
                    # Fetch avec filtre par année exacte
                    papers = fetcher.fetch(
                        query,
                        year_min=year,
                        year_max=year,
                        offset=offset
                    )

                    if not papers:
                        consecutive_empty += 1
                        if consecutive_empty >= 3:
                            print(f"Fin des résultats (offset: {offset})")
                            break
                        offset += fetcher.limit
                        continue

                    consecutive_empty = 0

                    # Traiter chaque article
                    for paper in papers:
                        total_fetched += 1
                        paper_id = paper.get("paperId")

                        if not paper_id:
                            continue

                        # Vérifier si déjà crawlé (fichiers JSONL)
                        if paper_id in existing_ids:
                            duplicates_year += 1
                            total_duplicates += 1
                            continue

                        # Nouvel article
                        existing_ids.add(paper_id)
                        count += 1
                        total_new += 1

                        # --- A. Construction de l'enregistrement JSONL ---
                        record = {
                            "publication": {
                                "id": paper_id,
                                "title": paper.get("title"),
                                "year": paper.get("year"),
                                "venue": paper.get("venue"),
                                "citation_count": paper.get("citationCount", 0),
                                "url": paper.get("url"),
                                "doi": paper.get("externalIds", {}).get("DOI"),
                                "abstract": paper.get("abstract"),
                                "references": paper.get("references", [])
                            },
                            "authors": [
                                {
                                    "id": author.get("authorId"),
                                    "externalIds":author.get("externalIds", {}),
                                    "name": author.get("name"),
                                    "affiliations": author.get("affiliations"),
                                    "hIndex":author.get("hIndex"),
                                }
                                for author in paper.get("authors", [])
                            ],
                            "fields_of_study": paper.get("fieldsOfStudy", [])
                        }

                        # Écrire dans le fichier JSONL
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")

                        # --- B. Insertion en base de données ---
                        research_item = ResearchItemCreate(
                            source_id=semantic_scholar.id,
                            external_id=paper_id,
                            doi=paper.get("externalIds", {}).get("DOI"),
                            title=paper.get("title"),
                            year=paper.get("year"),
                            type="paper",
                            abstract=paper.get("abstract"),
                            is_retracted=False,
                            is_open_access=paper.get("isOpenAccess"),
                            references=paper.get("references", []),
                            metrics={
                                "citation_count": paper.get("citationCount", 0),
                                "venue": paper.get("venue"),
                                "fields_of_study": paper.get("fieldsOfStudy", []),
                                "authors": paper.get("authors", []),
                                "url": paper.get("url")
                            },
                            raw=paper
                        )

                        # Gestion des doublons en DB
                        try:
                            item_service.create(session, research_item)
                            db_inserted_year += 1
                            total_db_inserted += 1
                        except IntegrityError:
                            # CRUCIAL : On réinitialise la session après un doublon DOI
                            session.rollback() 
                            db_duplicates_year += 1
                            total_db_duplicates += 1
                        except Exception as e:
                            session.rollback() # Obligatoire aussi ici !
                            # On ne compte pas ça comme un doublon, mais on affiche l'erreur
                            print(f"Erreur technique (hors doublon) : {e}")




                        # Affichage toutes les 100 nouveaux
                        if count % 100 == 0:
                            elapsed = time.time() - start_time
                            print(f"   {year} | {count:,} nouveaux | "
                                  f"{elapsed / 60:.0f}:{elapsed % 60:02.0f} | "
                                  f"{duplicates_year} doublons fichier | "
                                  f"{db_inserted_year} en DB | offset: {offset}")

                    # Passer au prochain batch
                    offset += fetcher.limit

                    # Pause pour respecter rate limit API
                    time.sleep(0.1)

                except Exception as e:
                    print(f"Erreur à offset {offset}: {e}")
                    offset += fetcher.limit
                    time.sleep(1)
                    continue

            print(f"{year} terminé : {count:,} nouveaux | "
                  f"{duplicates_year} doublons fichier | "
                  f"{db_inserted_year} insérés en DB")

# ========== RÉSUMÉ FINAL ==========
elapsed = time.time() - start_time


print(f"CRAWL TERMINÉ")
print(f"Statistiques fichiers JSONL :")
print(f"{total_new:,} NOUVEAUX articles")
print(f"{total_duplicates:,} doublons ignorés")
print(f"{total_fetched:,} articles récupérés au total")
print(f" Statistiques base de données :")
print(f"{total_db_inserted:,} articles insérés")
print(f"{total_db_duplicates:,} doublons DB ignorés")
print(f"Performance :")
print(f"Temps total : {elapsed / 60:.0f}:{elapsed % 60:02.0f} ({elapsed:.2f}s)")
if total_new > 0:
    print(f"Vitesse : {total_new / elapsed:.1f} articles/seconde")
print(f"Fichier : {output_file}")
