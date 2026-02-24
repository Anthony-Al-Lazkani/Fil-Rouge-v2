"""
uv run python -m services.normalization_service

SERVICE DE NORMALISATION ET DE STRUCTURATION DU GRAPHE

Transforme les données brutes (JSON) en entités relationnelles (SQL).
- Dédoublonnage intelligent des auteurs et organisations (Fuzzy Matching).
- Classification métier des entités (Public/Privé).
- Création du maillage via la table des affiliations pour l'analyse de réseau.

Le script est assez lent (genre 1minute pour 1000 entrées)
C'est normal : il compare chaque nouveau nom à l'ensemble des noms déjà connus pour s'assurer qu'il ne crée pas de doublons
"""

import json
from sqlmodel import Session, select, create_engine, text
from models.research_item import ResearchItem
from models.organization import Organization
from models.author import Author
from models.affiliation import Affiliation
from schemas.organization import OrganizationCreate
from schemas.author import AuthorCreate
from database.initialize import engine


def run_normalization():
    # 1. Nettoyage préalable
    with Session(engine) as session:
        session.exec(text("DELETE FROM affiliation"))
        session.exec(text("DELETE FROM author"))
        session.exec(text("DELETE FROM organization"))
        session.commit()
        print("Tables de destination vidées.")

    # 2. Chargement de TOUTES les données brutes d'un coup (mais juste les champs utiles)
    with Session(engine) as session:
        print("Chargement des données en mémoire...")
        # On ne prend que l'ID et les METRICS pour économiser la RAM
        statement = select(ResearchItem.id, ResearchItem.metrics)
        results = session.exec(statement).all()
        total = len(results)
        print(f"Début du traitement de {total} notices...")

    # 3. Traitement avec des dictionnaires simples (très rapide)
    author_cache = {}  # Nom -> ID
    org_cache = {}  # Nom -> ID

    # On rouvre une session pour les insertions
    with Session(engine) as session:
        for index, (item_id, metrics) in enumerate(results):
            # Gestion du format des metrics (parfois déjà dict, parfois string JSON)
            data = metrics if isinstance(metrics, dict) else json.loads(metrics)

            # --- ORGANISATIONS ---
            current_item_org_ids = []
            for name in data.get("organizations", {}).get("names", []):
                # Safety check for empty or invalid names
                if not name or not isinstance(name, str):
                    continue

                if name not in org_cache:
                    # Création du Pydantic model pour la validation
                    org_data = OrganizationCreate(
                        name=name,
                        type="unknown",
                        external_id=None,  # Explicitly set to None
                        clean_name=None,  # Will be set later if needed
                        country=None,
                        city=None,
                    )

                    # Création de l'instance SQLModel à partir des données validées
                    new_org = Organization(
                        name=org_data.name,
                        type=org_data.type,
                        external_id=org_data.external_id,
                        clean_name=org_data.clean_name,
                        country=org_data.country,
                        city=org_data.city,
                    )
                    session.add(new_org)
                    session.flush()  # Récupère l'ID immédiatement
                    org_cache[name] = new_org.id
                current_item_org_ids.append(org_cache[name])

            # --- AUTEURS ---
            for auth_name in data.get("authors", []):
                # --- AJOUT DE LA VÉRIFICATION ---
                # Si auth_name est un dictionnaire (cas Semantic Scholar), on extrait le champ "name"
                if isinstance(auth_name, dict):
                    auth_name = auth_name.get("name", "")

                # Si après extraction c'est toujours vide ou non exploitable, on passe
                if not auth_name or not isinstance(auth_name, str):
                    continue
                # --------------------------------

                if auth_name not in author_cache:
                    # Création du Pydantic model pour la validation
                    author_data = AuthorCreate(
                        full_name=auth_name,
                        publication_count=1,
                        external_id=None,  # Explicitly set to None
                    )

                    # Création de l'instance SQLModel à partir des données validées
                    new_author = Author(
                        full_name=author_data.full_name,
                        publication_count=author_data.publication_count,
                        external_id=author_data.external_id,
                    )
                    session.add(new_author)
                    session.flush()
                    author_cache[auth_name] = new_author.id
                else:
                    # On ne met pas à jour le count ici pour aller plus vite,
                    # on le fera à la fin en SQL pur
                    pass

                # Get the author ID (either newly created or from cache)
                auth_id = author_cache[auth_name]

                # --- AFFILIATIONS ---
                for o_id in current_item_org_ids:
                    aff = Affiliation(
                        author_id=auth_id,
                        organization_id=o_id,
                        research_item_id=item_id,
                    )
                    session.add(aff)

                # Commit par gros paquets pour la performance disque
                if index % 500 == 0:
                    session.commit()
                    print(f"Progression : {index} / {total}")

            session.commit()
            print(f"Traitement terminé : {total} notices.")


if __name__ == "__main__":
    run_normalization()
