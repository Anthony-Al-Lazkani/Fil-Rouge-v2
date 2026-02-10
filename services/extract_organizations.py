import re
import json
from sqlmodel import Session, select, create_engine
from models.research_item import ResearchItem
from models.organization import Organization
from models.affiliation import Affiliation
from schemas.organization import OrganizationCreate

# Connexion à la base
engine = create_engine("sqlite:///database.db")


def normalize_org_name(name):
    """
    Normalisation spécifique pour les organisations.
    Ex: "Université Paris-Saclay" -> "universite paris saclay"
    """
    if not name:
        return ""
    name = name.lower()
    # On retire les points, tirets et parenthèses
    name = re.sub(r"[.\-\(\)\[\]]", " ", name)
    # On remplace les accents courants pour faciliter le regroupement
    name = name.replace("é", "e").replace("è", "e").replace("ê", "e").replace("à", "a")
    name = " ".join(name.split())
    return name


def run_organization_extraction():
    with Session(engine) as session:
        print("--- Démarrage de l'extraction des organisations ---")

        # 1. Nettoyage : On ne vide PAS Author, mais on vide Organization
        # et on remet à plat les liens dans Affiliation pour les organisations
        session.exec(Organization.__table__.delete())
        session.commit()
        print("Table Organization réinitialisée.")

        # 2. Cache : Empreinte (Nom+Pays) -> ID
        org_cache = {}

        # 3. Récupération des articles
        items = session.exec(select(ResearchItem)).all()
        total = len(items)

        for index, item in enumerate(items):
            metrics = item.metrics
            if not isinstance(metrics, dict):
                try:
                    metrics = json.loads(metrics) if metrics else {}
                except:
                    metrics = {}

            org_data = metrics.get("organizations", {})
            names = org_data.get("names", [])
            types = org_data.get("types", [])
            countries = org_data.get("countries", [])

            # On boucle sur les organisations citées dans l'article
            for i in range(len(names)):
                raw_name = names[i]
                if not raw_name:
                    continue

                org_type = types[i] if i < len(types) else None
                country = countries[i] if i < len(countries) else None

                # Empreinte pour le dédoublonnage
                fingerprint = f"{normalize_org_name(raw_name)}|{country or ''}"

                if fingerprint not in org_cache:
                    # Création du Pydantic model pour la validation
                    org_data = OrganizationCreate(
                        name=raw_name.strip(), type=org_type, country=country
                    )

                    # Création de l'instance SQLModel à partir des données validées
                    new_org = Organization(
                        name=org_data.name, type=org_data.type, country=org_data.country
                    )
                    session.add(new_org)
                    session.flush()
                    org_cache[fingerprint] = new_org.id

                # 4. MISE À JOUR DE L'AFFILIATION
                # Attention : Ici, nous devons lier cette organisation à l'article.
                # Comme un article peut avoir plusieurs auteurs et plusieurs orgs,
                # HAL lie souvent globalement les orgs à l'article.
                # Pour simplifier à ce stade, nous lions l'organisation à l'article dans Affiliation.

                # On cherche les affiliations existantes pour cet article
                # et on leur assigne l'organisation (approche simplifiée)
                affiliations = session.exec(
                    select(Affiliation).where(Affiliation.research_item_id == item.id)
                ).all()

                for aff in affiliations:
                    aff.organization_id = org_cache[fingerprint]
                    session.add(aff)

            if index % 500 == 0:
                session.commit()
                print(f"Traitement : {index} / {total} articles...")

        session.commit()
        print(f"\nExtraction terminée. {len(org_cache)} organisations identifiées.")


if __name__ == "__main__":
    run_organization_extraction()
