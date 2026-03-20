"""
normalisation_typeEntity.py
Normalise le champ 'type' de la table entity dans database.db.
Valeurs cibles : company, education, facility, investor, nonprofit, government
Possibilité de combiner : "facility, education"
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "database.db"

#Mots-clés de détection
ENTREPRISE_KW = [
    "company", "société", "societe", "sas,", "sasu,", "sarl",
    "aktiengesellschaft", "corporation", "gie",
    "responsabilité limitée", "actions simplifiée",
    "actions simplifiee", "par actions", "s.a.", "entité étrangère",
]

NONPROFIT_KW = [
    "association", "non-profit", "not-for-profit", "nonprofit",
    "non-soliciting", "not-soliciting", "soliciting",
]

EDUCATION_KW = [
    "ecole", "école", "school", "education", "éducation", "institut", "institute",
    "enseignement", "académie", "academie", "academy", "universit",
    "college", "collège", "mines", "polytechnique", "supérieur",
    "superieur", "higher", "faculty", "faculté", "faculte",
]

def classify_type(raw_type: str, display_name: str) -> str:
    """
    Retourne le type normalisé.
    raw_type : valeur actuelle du champ type
    display_name : nom de l'entité (pour détecter education dans les facility)
    """
    t = (raw_type or "").strip().lower()
    name = (display_name or "").strip().lower()

    # Déjà normalisés
    if t == "company":
        return "company"
    if t == "education":
        return "education"
    if t == "investor":
        return "investor"
    if t == "government" or t == "governement":
        return "government"
    if t == "facility, education":
        return "facility, education"

    # Facility : vérifier si c'est aussi education
    if t == "facility":
        if any(kw in name for kw in EDUCATION_KW):
            return "facility, education"
        return "facility"

    # Société civile → nonprofit (avant le test entreprise car "société" matcherait)
    if "société civile" in t or "societe civile" in t:
        return "nonprofit"

    # Nonprofit
    if any(kw in t for kw in NONPROFIT_KW):
        return "nonprofit"

    # Entreprise
    if any(kw in t for kw in ENTREPRISE_KW):
        return "company"

    # Inconnu : on laisse tel quel
    if t:
        print(f"Type non classifié : '{raw_type}' (entité: {display_name})")
        return raw_type

    return ""


def normaliser():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, type, display_name, name FROM entity").fetchall()
    total = len(rows)
    modified = 0

    for i, r in enumerate(rows, 1):
        raw_type = r["type"] or ""
        display_name = r["display_name"] or r["name"] or ""
        new_type = classify_type(raw_type, display_name)

        if new_type != raw_type:
            conn.execute("UPDATE entity SET type = ? WHERE id = ?", (new_type, r["id"]))
            modified += 1

        if i % 500 == 0:
            print(f"{i}/{total} entités traitées ({modified} modifiées)")

    conn.commit()
    conn.close()
    print(f"\nTerminé : {modified}/{total} entités modifiées")

if __name__ == "__main__":
    print("Normalisation des types d'entités")
    normaliser()
