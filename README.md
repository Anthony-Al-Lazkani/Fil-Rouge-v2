# Fil-Rouge

Ce projet constitue une infrastructure de collecte et de traitement de données hétérogènes pour cartographier l'écosystème de l'Intelligence Artificielle. Il unifie les données de la recherche académique, de la propriété industrielle et des registres légaux.

## USAGE:
    Penser à autoriser l'application sur le portail développeur EPO (validité 20 min) (l'appli s'appelle : fil-rouge-v2-inpi-ai)
    https://developers.epo.org/user/31706/app-detail/ed3afe02-dce8-47ef-a214-fd5a96a82652
---

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

### 2. La partie EXPLOITATION DANS GRAPHDB via une ONTOLOGIE
---

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

---

## Configuration et Pilotage

Le fichier `pipeline.py` centralise l'exécution. 
Chaque source est pilotable depuis le script par des variables de contrôle pour ajuster la profondeur et la précision du crawl.

### Commandes principales
# réinitaliser la BDD (utile lors des tests):
uv run reset_db.py 

# Lancer la collecte totale (limites par défaut)
uv run scripts/pipeline.py

# Arguments possibles
--source (arxiv/hal/inpi/open_alex/open_alex_institution/open_corporates/scanr/s2) 
--query "machine learning" 
--limit 100


## Principes de Normalisation

* **Alignement des thématiques** : Les champs `topics` des items de recherche sont strictement synchronisés avec les `industries` de l'entité rattachée pour garantir la cohérence des filtres.
* **Neutralisation des types** : Les formes juridiques spécifiques (SAS, GIE, etc.) sont simplifiées en 'company' dans le champ `type` de `entity` pour faciliter le requêtage SQL, tout en conservant le détail brut dans l'objet `raw`.
* **Gestion du Throttling** : Chaque crawler intègre des délais de latence (time.sleep) calibrés selon les limitations spécifiques des serveurs (particulièrement restrictif pour l'EPO et ArXiv).

## Stack Technique
    Langage : Python 3.12+
    Base de données : PostgreSQL (via SQLModel)
    Environnement : Gestion via uv ou venv