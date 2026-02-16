# Fil-Rouge

# Workflow actuel:
uv run python -m database.initialize (si on veut réinitialiser la BDD)
uv run uvicorn main:app --reload

uv run python -m crawlers.Hal_Bulk_Publications
uv run python -m crawlers.arxiv_crawler
uv run python -m crawlers.semantic_scholar_main
uv run python -m crawlers.open_alex_crawler
uv run python -m crawlers.Inpi_Bulk

uv run python -m services.normalization_doublons

uv run python -m services.extract_authors
uv run python -m services.extract_organizations

uv run ontologie/peupler_ontologie.py 

16-02-2026:
     Travail sur un prototype d'ontologie

04-02-2026:
     Ajout du script normalization_doublons.py pour supprimer les doublons de la base de données.
     Modification de la structure de la table pour que le DOI soit unique=True
     Modification du crawler semantic_scholar (années 2021 à 2026) + gestion des exceptions (notamment vis à vis de l'unicité du DOI)
     Ajout du scrit extract_authors et extract_organizations qui remplissent les tables

03-02-2026:
     Choix à faire entre passer par Ontotext/refine ou par faire un script Python qui va nettoyer les doublons et enrichir la BDD
     Je tente de faire un script qui l'enrichit, cela permet d'avoir quelque chose d'automatique.
     Ajout de nouvelles tables dans la base:
          models/organization.py : Le référentiel des entités (pour distinguer Public/Privé).
          models/author.py : Le référentiel des auteurs (pour le dédoublonnage).
          models/affiliation.py : La table pivot qui fait le maillage (Qui ? Où ? Quoi ?).
     services/normalization_service.py : Le moteur qui extrait les données des JSON pour remplir ces tables
     Après il faudra mettre le tout dans Jena / Fuseki

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