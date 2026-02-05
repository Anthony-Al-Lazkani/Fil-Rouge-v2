# '''
# Parcourt la table ResearchItem à la recherche de doublons sur les doi et les supprime de la base
# A lancer en stand alone:
# uv run python -m services.normalization_doublons
# '''
#
#
# import sqlite3
# import csv
#
# def nettoyer_et_analyser_doublons():
#     conn = sqlite3.connect('database.db')
#     cursor = conn.cursor()
#
#     # 1. Identification avant suppression (pour le rapport)
#     query_avant = """
#     SELECT doi, source_id, title, year, external_id
#     FROM researchitem
#     WHERE doi IN (
#         SELECT doi FROM researchitem
#         WHERE doi IS NOT NULL
#         GROUP BY doi HAVING COUNT(*) > 1
#     )
#     ORDER BY doi;
#     """
#     cursor.execute(query_avant)
#     doublons_identifies = cursor.fetchall()
#
#     if not doublons_identifies:
#         print("Aucun doublon trouvé. La base est déjà saine.")
#         conn.close()
#         return
#
#     print(f"Identification de {len(doublons_identifies)} lignes de doublons (potentiels).")
#
#     # 2. Suppression des doublons
#     # On garde l'entrée avec l'ID le plus petit (le premier inséré) pour chaque DOI
#     delete_query = """
#     DELETE FROM researchitem
#     WHERE id NOT IN (
#         SELECT MIN(id)
#         FROM researchitem
#         WHERE doi IS NOT NULL
#         GROUP BY doi
#     )
#     AND doi IS NOT NULL;
#     """
#
#     try:
#         cursor.execute(delete_query)
#         nb_supprimes = cursor.rowcount
#         conn.commit()
#         print(f"Nettoyage terminé : {nb_supprimes} doublons supprimés de la base de données.")
#     except Exception as e:
#         conn.rollback()
#         print(f"Erreur lors de la suppression : {e}")
#         conn.close()
#         return
#
#     # 3. Exportation du rapport de ce qui a été traité
#     with open('doublons_traites.csv', 'w', newline='', encoding='utf-8') as f:
#         writer = csv.writer(f)
#         writer.writerow(['DOI', 'Source_ID', 'Titre', 'Année', 'ID_Externe'])
#         writer.writerows(doublons_identifies)
#
#     conn.close()
#     print(f"Rapport des anciens doublons exporté dans 'doublons_traites.csv'")
#
# if __name__ == "__main__":
#     nettoyer_et_analyser_doublons()


"""
Parcourt la table ResearchItem à la recherche de doublons sur les DOI et les supprime de la base.
Exporte un rapport des doublons supprimés dans un CSV.
A lancer en stand alone:
uv run python -m services.normalization_doublons
"""

import csv
from sqlmodel import Session, select, func
from models.research_item import ResearchItem
from database.initialize import engine


def nettoyer_et_analyser_doublons():
    with Session(engine) as session:
        # 1️⃣ Identifier les DOI qui ont des doublons
        duplicates_stmt = (
            select(ResearchItem.doi)
            .where(ResearchItem.doi is not None)
            .group_by(ResearchItem.doi)
            .having(func.count(ResearchItem.id) > 1)
        )
        duplicate_dois = session.exec(duplicates_stmt).all()

        if not duplicate_dois:
            print("Aucun doublon trouvé. La base est déjà saine.")
            return

        print(f"Identification de {len(duplicate_dois)} DOI en doublon (potentiels).")

        report_rows = []

        # 2️⃣ Supprimer uniquement les doublons réels
        for doi_tuple in duplicate_dois:
            doi = doi_tuple[0] if isinstance(doi_tuple, tuple) else doi_tuple
            # Récupérer toutes les entrées pour ce DOI
            items_stmt = select(ResearchItem).where(ResearchItem.doi == doi)
            items = session.exec(items_stmt).all()

            # Garder l'entrée avec l'ID le plus petit
            keep_item = min(items, key=lambda x: x.id)
            to_delete = [i for i in items if i.id != keep_item.id]

            for dup in to_delete:
                report_rows.append([
                    dup.doi,
                    dup.source_id,
                    dup.title,
                    dup.year,
                    dup.external_id
                ])
                session.delete(dup)

        # Commit final
        session.commit()
        print(f"Nettoyage terminé : {len(report_rows)} doublons supprimés.")

        # 3️⃣ Export CSV pour audit
        with open("doublons_traites_safe.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["DOI", "Source_ID", "Titre", "Année", "ID_Externe"])
            writer.writerows(report_rows)

        print("Rapport exporté dans 'doublons_traites_safe.csv'")


if __name__ == "__main__":
    nettoyer_et_analyser_doublons()
