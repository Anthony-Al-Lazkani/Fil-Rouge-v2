# Fil-Rouge

Ce projet constitue une infrastructure de collecte et de traitement de données hétérogènes pour cartographier l'écosystème de l'Intelligence Artificielle. Il unifie les données de la recherche académique, de la propriété industrielle et des registres légaux.

## USAGE:
    Penser à autoriser l'application sur le portail développeur EPO (validité 20 min) (l'appli s'appelle : fil-rouge-v2-inpi-ai)
    https://developers.epo.org/user/31706/app-detail/ed3afe02-dce8-47ef-a214-fd5a96a82652

## Configuration et Pilotage
Le fichier `pipeline.py` centralise l'exécution. 
Chaque source est pilotable depuis le script par des variables de contrôle pour ajuster la profondeur et la précision du crawl.

### Commandes principales
# réinitaliser la BDD (utile lors des tests):
uv run reset_db.py 

# Lancer la collecte totale (limites par défaut)
uv run scripts/pipeline.py

## Arguments possibles
--source (arxiv/hal/inpi/open_alex/open_alex_institution/open_corporates/scanr/s2) 
--query "machine learning" 
--limit 100

# Enrichir la base avec les scripts de peuplement:
uv run ./scripts/pipeline_normalization.py


## Architecture du Système
Le projet est articulé autour de deux grands piliers:

### 1. La partie CRAWLING et INJECTION en BDD SQL :

#### A. Crawlers
Modules spécialisés dans la récupération de données brutes. 
Ils gèrent les spécificités techniques de chaque source :
* **APIs REST / JSON** : ScanR, OpenCorporates.
* **Flux Atom / XML** : ArXiv, HAL, EPO (OPS).
* **Wrappers spécialisés** : PyAlex pour OpenAlex.

### B. Processors
Couche de logique métier chargée de :
* Le nettoyage et la normalisation des chaînes de caractères.
* Le mapping et l'insertion dans la BDD

### C. Models
Structure de données unifiée utilisant SQLModel :
* **Entity** : Entreprises, laboratoires, institutions.
* **ResearchItem** : Publications, preprints, brevets.
* **Source** : Traçabilité de l'origine des données.
* **Author** : pour lister les auteurs
* **Affiliation** : pour faire des liens permettant la génération ultérieure de triplets

### D. Pipeline de Consolidation Relationnelle
Une fois les données injectées, le système exécute un pipeline coordonné (scripts/normalisation.py) qui transforme les données brutes en un graphe de connaissances cohérent. 
Ce pipeline orchestre quatre étapes clés :
1. **Normalisation géographique** : Standardise les noms de pays et codes ISO (ex: "France", "FR", "FRA" => "France").
2. **Linker Flexible (Auteurs)** : Identifie les auteurs et crée les liens `Auteur <-> ResearchItem`. Il normalise les identités et met à jour les compteurs de publications.
3. **Org Linker (Organisations)** : Enrichit les liens existants en identifiant les `Entity` (Universités, Entreprises) grâce aux pivots ROR et aux domaines d'emails institutionnels (+une recherche "plein texte" sécurisée pour éviter le bruit sémantique.)
4. **Matching Entrepreneur** : Croise les auteurs académiques avec les fondateurs de Crunchbase (clé Founders) et les dirigeants de ScanR (clé leaders).
    * **Réconciliation d'Identité** : Analyse de similarité entre les auteurs de publications et les fondateurs de startups (>80%) présents dans la base.
    * **Inférence de Rôle** : Marque les profils comme `:Entrepreneur` dans l'ontologie.
    * **Analyse de Transfert** : Permet de requêter les chercheurs ayant valorisé leurs travaux via la création d'entreprise.


### 2. La partie EXPLOITATION DANS GRAPHDB via une ONTOLOGIE
Cette seconde phase transforme les données relationnelles en un graphe de connaissances sémantique permettant des requêtes d'inférence complexes.

#### A. Ontologie S2B
Les données sont structurées selon une ontologie OWL (S2B_Ontology) qui définit les pivots du domaine :
Classes : Chercheur, Entrepreneur, Startup, Brevet, TravailDeRecherche.
Relations : collaboreAvec, estAffilieA, deriveDe (lien Brevet/Article), estLocaliseEn.

#### B. Pipeline de Peuplement (RDFLib)
Le script peupler_robuste.py assure la transition SQL vers RDF :
    Extraction des instances depuis database.db.
    Génération de triplets au format Turtle (.ttl).
    Mapping des types (ex: une Entity de type 'univ' devient une instance de la classe Université).

#### C. Intégration GraphDB
Une suite de scripts automatise l'ingestion dans l'instance GraphDB :
    Initialisation : setup_graphdb.py crée le repository via repo-config.ttl.
    Import : import_ontoGraphdb.py charge la structure de l'ontologie.
    Injection : insertion_graphdb.py pousse les données peuplées via l'API RDF4J.

## Sources et Identifiants
Le pipeline utilise des identifiants pivots pour permettre le croisement des données :

| Source | Nature des données | Pivot Identité | Pivot Recherche |
| :--- | :--- | :--- | :--- |
| data | Fichiers CSV contenant quelques données chiffrées sur des entreprises |
| ScanR | Recherche & Innovation FR | SIREN / ROR | Patent ID |
| OpenAlex | Littérature mondiale | ROR | DOI |
| ArXiv | Preprints IA (CS) | - | ArXiv ID |
| HAL | Archive ouverte FR | StructID | DOI |
| EPO / INPI | Propriété industrielle | Applicant Name | DOCDB ID |
| OpenCorporates | Registre légal mondial | Company Number | - |


## Principes de Normalisation
* **Alignement des thématiques** : Les champs `topics` des items de recherche sont strictement synchronisés avec les `industries` de l'entité rattachée pour garantir la cohérence des filtres.
* **Neutralisation des types** : Les formes juridiques spécifiques (SAS, GIE, etc.) sont simplifiées en 'company' dans le champ `type` de `entity` pour faciliter le requêtage SQL, tout en conservant le détail brut dans l'objet `raw`.
* **Gestion du Throttling** : Chaque crawler intègre des délais de latence (time.sleep) calibrés selon les limitations spécifiques des serveurs (particulièrement restrictif pour l'EPO et ArXiv).

## Stack Technique
    Langage : Python 3.12+
    Base de données : PostgreSQL (via SQLModel)
    Environnement : Gestion via uv ou venv