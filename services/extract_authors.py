import re
import json
from sqlmodel import Session, select, create_engine
from models.research_item import ResearchItem
from models.author import Author
from models.affiliation import Affiliation
from schemas.author import AuthorCreate

# Assurez-vous que le chemin est correct vers votre base
engine = create_engine("sqlite:///database.db")


def normalize_name(name):
    """
    Crée une signature normalisée pour un nom afin de faciliter le dédoublonnage.
    Ex: "Adrien F. Vincent" -> "adrien f vincent"
    """
    if not name:
        return ""
    # Passage en minuscules
    name = name.lower()
    # Suppression de la ponctuation (points, tirets remplacés par espace)
    name = re.sub(r"[.\-]", " ", name)
    # Suppression des espaces multiples et invisibles
    name = " ".join(name.split())
    return name


def run_author_extraction():
    with Session(engine) as session:
        print("--- Démarrage de l'extraction intelligente des auteurs ---")

        # 1. Nettoyage préalable
        session.exec(Affiliation.__table__.delete())
        session.exec(Author.__table__.delete())
        session.commit()
        print("Tables Author et Affiliation réinitialisées.")

        # 2. Cache : Clé = Nom Normalisé (fingerprint), Valeur = ID en base
        author_cache = {}

        # 3. Récupération des articles
        items = session.exec(select(ResearchItem)).all()
        total = len(items)
        print(f"Analyse de {total} articles en cours...")

        for index, item in enumerate(items):
            # Gestion robuste du JSON (au cas où ce soit déjà un dict ou une string)
            metrics = item.metrics
            if not isinstance(metrics, dict):
                try:
                    metrics = json.loads(metrics) if metrics else {}
                except (ValueError, TypeError):
                    metrics = {}

            author_names = metrics.get("authors", [])

            for raw_name in author_names:
                if not raw_name:
                    continue

                # --- AJOUT DE LA VÉRIFICATION ---
                # Si raw_name est un dictionnaire (cas Semantic Scholar), on extrait le champ "name"
                if isinstance(raw_name, dict):
                    raw_name = raw_name.get("name", "")

                # Si après extraction c'est toujours vide ou non exploitable, on passe
                if not raw_name or not isinstance(raw_name, str):
                    continue
                # --------------------------------

                # Le reste du script reste identique
                fingerprint = normalize_name(raw_name)

                # Si le nom est vide après nettoyage (ex: "."), on ignore
                if not fingerprint:
                    continue

                # Vérification dans le cache via l'empreinte
                if fingerprint not in author_cache:
                    # C'est un nouvel auteur pour nous
                    # Création du Pydantic model pour la validation
                    author_data = AuthorCreate(
                        full_name=raw_name.strip(), publication_count=1
                    )

                    # Création de l'instance SQLModel à partir des données validées
                    new_author = Author(
                        full_name=author_data.full_name,
                        publication_count=author_data.publication_count,
                    )
                    session.add(new_author)
                    session.flush()  # Récupère l'ID généré par la BDD

                    # On enregistre l'ID dans le cache face à son empreinte
                    author_cache[fingerprint] = new_author.id
                else:
                    # L'auteur existe déjà, on récupère son ID
                    author_id = author_cache[fingerprint]

                    # Optionnel : On pourrait incrémenter le compteur ici via une requête,
                    # mais pour la performance, on fera un COUNT(*) global plus tard.

                # Création du lien Article <-> Auteur
                # Note: organization_id sera NULL par défaut, ce qui est valide maintenant.
                affiliation = Affiliation(
                    author_id=author_cache[fingerprint], research_item_id=item.id
                )
                session.add(affiliation)

            # Commit par lots de 500 pour ne pas saturer la mémoire
            if index % 500 == 0:
                session.commit()
                print(f"Traitement : {index} / {total} articles...")

        session.commit()
        print(f"\nTerminé ! {len(author_cache)} auteurs uniques identifiés et liés.")


if __name__ == "__main__":
    run_author_extraction()
