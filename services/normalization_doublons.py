'''
Parcourt la table ResearchItem à la recherche de doublons sur les doi et les supprime de la base
A lancer en stand alone:
uv run python -m services.normalization_doublons
'''


import sqlite3
import csv

def nettoyer_et_analyser_doublons():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # 1. Identification avant suppression (pour le rapport)
    query_avant = """
    SELECT doi, source_id, title, year, external_id
    FROM researchitem
    WHERE doi IN (
        SELECT doi FROM researchitem 
        WHERE doi IS NOT NULL 
        GROUP BY doi HAVING COUNT(*) > 1
    )
    ORDER BY doi;
    """
    cursor.execute(query_avant)
    doublons_identifies = cursor.fetchall()
    
    if not doublons_identifies:
        print("Aucun doublon trouvé. La base est déjà saine.")
        conn.close()
        return

    print(f"Identification de {len(doublons_identifies)} lignes de doublons (potentiels).")

    # 2. Suppression des doublons
    # On garde l'entrée avec l'ID le plus petit (le premier inséré) pour chaque DOI
    delete_query = """
    DELETE FROM researchitem
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM researchitem
        WHERE doi IS NOT NULL
        GROUP BY doi
    )
    AND doi IS NOT NULL;
    """
    
    try:
        cursor.execute(delete_query)
        nb_supprimes = cursor.rowcount
        conn.commit()
        print(f"Nettoyage terminé : {nb_supprimes} doublons supprimés de la base de données.")
    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de la suppression : {e}")
        conn.close()
        return

    # 3. Exportation du rapport de ce qui a été traité
    with open('doublons_traites.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['DOI', 'Source_ID', 'Titre', 'Année', 'ID_Externe'])
        writer.writerows(doublons_identifies)
    
    conn.close()
    print(f"Rapport des anciens doublons exporté dans 'doublons_traites.csv'")

if __name__ == "__main__":
    nettoyer_et_analyser_doublons()