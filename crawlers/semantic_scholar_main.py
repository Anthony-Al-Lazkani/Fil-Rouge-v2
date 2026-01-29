from semantic_scholar_fetcher import SemanticScholarFetcher
from datetime import datetime
from pathlib import Path
import json
import time
import glob

# ========== CONFIGURATION ==========
QUERY = "artificial intelligence"
YEARS = [2022, 2023, 2024, 2025]  # ← Une requête par année
MAX_PER_YEAR = 2500  # 4 années × 2500 = 10,000 articles
API_KEY = "BJxxqhUWGI2QmwHvezhLqasQc0I3Sq2e5HrdxnCi"


# ===================================


def load_existing_ids(data_folder="data"):
    """Charge tous les IDs d'articles déjà crawlés"""
    existing_ids = set()
    jsonl_files = glob.glob(f"{data_folder}/semantic_scholar_*.jsonl")

    if not jsonl_files:
        print("📭 Aucun fichier précédent trouvé\n")
        return existing_ids

    print(f"🔍 Vérification de {len(jsonl_files)} fichier(s) existant(s)...")

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
            print(f"⚠️  Erreur lecture {filepath}: {e}")

    print(f"✅ {len(existing_ids):,} articles déjà crawlés\n")
    return existing_ids


# Créer le dossier data
Path("data").mkdir(parents=True, exist_ok=True)

# Charger les IDs existants
existing_ids = load_existing_ids()

# Créer le fichier de sortie avec timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = Path("data") / f"semantic_scholar_{timestamp}.jsonl"

# Initialiser le fetcher
fetcher = SemanticScholarFetcher(api_key=API_KEY, limit=100)

print(f"📂 Fichier de sortie : {output_file}")
print(f"🔍 Requête : '{QUERY}'")
print(f"📅 Années : {YEARS}")
print(f"🎯 Objectif : {len(YEARS) * MAX_PER_YEAR:,} NOUVEAUX articles maximum\n")

# Compteurs globaux
total_new = 0
total_duplicates = 0
total_fetched = 0
start_time = time.time()

# Ouvrir le fichier en mode append
with open(output_file, "a", encoding="utf-8") as f:
    # ========== BOUCLE PAR ANNÉE ==========
    for year in YEARS:
        print(f"\n{'=' * 60}")
        print(f"📅 ANNÉE {year}")
        print(f"{'=' * 60}\n")

        count = 0
        offset = 0
        duplicates_year = 0
        consecutive_empty = 0

        while count < MAX_PER_YEAR:
            try:
                # Fetch avec filtre par année exacte
                papers = fetcher.fetch(
                    QUERY,
                    year_min=year,
                    year_max=year,  # ← Limite à cette année précise
                    offset=offset
                )

                if not papers:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        print(f"❌ Fin des résultats pour {year} (offset: {offset})\n")
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

                    # Vérifier si déjà crawlé
                    if paper_id in existing_ids:
                        duplicates_year += 1
                        total_duplicates += 1
                        continue

                    # Nouvel article !
                    existing_ids.add(paper_id)
                    count += 1
                    total_new += 1

                    # Construire l'enregistrement
                    record = {
                        "crawl_date": datetime.now().isoformat(),
                        "source": "semantic_scholar",
                        "query": QUERY,
                        "year_filter": year,
                        "publication": {
                            "id": paper_id,
                            "title": paper.get("title"),
                            "year": paper.get("year"),
                            "venue": paper.get("venue"),
                            "citation_count": paper.get("citationCount", 0),
                            "url": paper.get("url"),
                            "abstract": paper.get("abstract")
                        },
                        "authors": [
                            {
                                "id": author.get("authorId"),
                                "name": author.get("name")
                            }
                            for author in paper.get("authors", [])
                        ]
                    }

                    # Écrire dans le fichier
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

                    # Affichage toutes les 100 nouveaux
                    if count % 100 == 0:
                        elapsed = time.time() - start_time
                        print(f"📊 {year} | {count:,} nouveaux | ⏱️  {elapsed / 60:.0f}:{elapsed % 60:02.0f} | "
                              f"🚫 {duplicates_year} doublons | offset: {offset}")

                # Passer au prochain batch
                offset += fetcher.limit

                # Pause si besoin (respect API rate limit)
                time.sleep(0.1)

            except Exception as e:
                print(f"⚠️  Erreur à offset {offset}: {e}")
                offset += fetcher.limit
                time.sleep(1)
                continue

        print(f"\n✅ {year} terminé : {count:,} nouveaux articles | {duplicates_year} doublons")

# ========== RÉSUMÉ FINAL ==========
elapsed = time.time() - start_time

print(f"\n{'=' * 60}")
print(f"✅ CRAWL TERMINÉ")
print(f"{'=' * 60}")
print(f"🆕 {total_new:,} NOUVEAUX articles")
print(f"🚫 {total_duplicates:,} doublons ignorés")
print(f"📥 {total_fetched:,} articles récupérés au total")
print(f"⏱️  Temps réel : {elapsed / 60:.0f}:{elapsed % 60:02.0f} ({elapsed:.2f} secondes)")
if total_new > 0:
    print(f"📈 Vitesse : {total_new / elapsed:.1f} nouveaux articles/seconde")
print(f"📂 Fichier : {output_file}")
print(f"{'=' * 60}\n")
