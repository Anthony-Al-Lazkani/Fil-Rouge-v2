# Fil-Rouge
02-02-2026:
     Amélioration du crawler Hal pour compléter la base de données
     -> ajout du doi, des auteurs et du pays de chaque auteur.
     -> visualisation des 100 premières lignes dans les jsonl pour visualiser l'échantillon
     Depuis 2021 (Intelligence artificielle -> 1710 articles / Artifical Intelligence -> 8712 articles collectés)

29-01-2026:
     Réinitialisation du repo sur GitHub
     Fusion des différentes branches et déménagement sur l'autre repo
     Mise à jour des scripts pour que ça marche

28-01-2026:
    Retour sur INPI pour appliquer l'ETL suivant:
    SEARCH  →  (family_id, doc_id)
             ↓
        DÉDUPLICATION (family)
             ↓
        BIBLIO + ABSTRACT
             ↓
        NORMALISATION
             ↓
        JSONL propre

27-01-2026:
    INPI: uv run Inpi_Bulk.py (attention ça va ajouter les lignes à epo_ai_refs.jsonl)
    reprendre la recherche depuis 2000
    Ensuite, exploiter les autres endpoint de l'api https://developers.epo.org/apis/ops-v32#/Published/Published%20Data%20Keywords%20Search%20without%20Consituents
    Récupération des 500 lignes de Crunchbase

21-01-2026:
    Finir d'obtenir ses accès pour INPI pour pouvoir terminer le scrapper
    HAL ne contient pas de champs "country". En tout cas, aucun des 2000 articles récupérés ne l'avait renseigné.