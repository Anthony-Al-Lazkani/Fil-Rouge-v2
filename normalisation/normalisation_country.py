import sqlite3
import unicodedata
from pathlib import Path

import pycountry
from babel import Locale

DB_PATH = Path(__file__).parent.parent / "database.db"

# --- 1. Mapping français → anglais via Babel ---
FR_TO_EN = {}
locale_fr = Locale("fr")
for country in pycountry.countries:
    nom_fr = locale_fr.territories.get(country.alpha_2)
    if nom_fr:
        FR_TO_EN[nom_fr.lower()] = country.name

# --- 2. Cas manuels ---
MANUAL_MAP = {
    "usa": "United States",
    "us": "United States",
    "uk": "United Kingdom",
    "england": "United Kingdom",
    "angleterre": "United Kingdom",
    "etats-unis": "United States",
    "ca_on": "Canada",
    "ca_qb": "Canada",
    "ca_bc": "Canada",
    "ca_ab": "Canada",
    "ca_qc": "Canada",
    "kosovo": "Kosovo",
    "santa clara": "United States",
    "turkey": "Turkiye",
    "turkiye": "Turkiye",
    "guadeloupe": "France",
    "reunion": "France",
    "ire": "Ireland",
    "jap": "Japan",
    "nig": "Nigeria",
    "por": "Portugal",
    "sou": "South Korea",
    "spa": "Spain",
    "swi": "Switzerland",
    "": None,
    "-": None,
    "the": "Netherlands",
    "uni": "United Kingdom",
}


def ascii_safe(name: str) -> str:
    """Supprime les accents pour compatibilité GraphDB."""
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")


def normalize_country(raw: str) -> str | None:
    if not raw:
        return None

    cleaned = raw.strip().strip(",").lower()

    if cleaned in MANUAL_MAP:
        return ascii_safe(MANUAL_MAP[cleaned])

    if cleaned in FR_TO_EN:
        return ascii_safe(FR_TO_EN[cleaned])

    try:
        return ascii_safe(pycountry.countries.lookup(cleaned).name)
    except LookupError:
        pass

    print(f"⚠️ Pays non reconnu : '{raw}' → cleaned: '{cleaned}'")
    return None


def main():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT country_code FROM entity WHERE country_code IS NOT NULL")
    distinct = [row[0] for row in cursor.fetchall()]
    print(f"{len(distinct)} valeurs distinctes de country_code\n")

    cursor.execute("SELECT id, country_code FROM entity WHERE country_code IS NOT NULL")
    rows = cursor.fetchall()
    total = len(rows)

    non_reconnus = set()
    for i, (row_id, raw) in enumerate(rows):
        if i % 1000 == 0:
            print(f"{i}/{total}...")

        normalized = normalize_country(raw)

        if normalized is None:
            non_reconnus.add(raw.strip().strip(",").lower())
            normalized = ascii_safe(raw.strip().strip(",").title())

        cursor.execute(
            "UPDATE entity SET country_code = ? WHERE id = ?",
            (normalized, row_id)
        )

    conn.commit()
    conn.close()

    print(f"\n✅ {total} lignes traitées")
    if non_reconnus:
        print(f"\n⚠️ {len(non_reconnus)} valeurs non reconnues à ajouter dans MANUAL_MAP :")
        for v in sorted(non_reconnus):
            print(f'    "{v}": "???",')


if __name__ == "__main__":
    main()
