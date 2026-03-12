"""
À partir de la base de données, peuple l'ontologie dans GraphDB
"""
import sqlite3
from pathlib import Path

import requests
import re
import time

GRAPHDB_URL = "http://localhost:7200"
REPO_ID = "fil-rougev2"
DB_PATH = Path(__file__).parent.parent / "database.db"
PREFIX = "http://www.semanticweb.org/s2b/ontologie#"
LIMIT = 100

session = requests.Session()


def sparql_update(query):
    full = f"PREFIX : <{PREFIX}>\nPREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n{query}"
    try:
        r = session.post(
            f"{GRAPHDB_URL}/repositories/{REPO_ID}/statements",
            headers={"Content-Type": "application/sparql-update"},
            data=full
        )
        if r.status_code == 204:
            return True
        else:
            print(f"❌ {r.status_code} - {r.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print("⏳ Pause connexion...")
        time.sleep(5)
        return sparql_update(query)


def clean_uri(text):
    if not text:
        return "unknown"
    text = text.strip().replace(" ", "_").replace("'", "").replace('"', '')
    text = re.sub(r'[^a-zA-Z0-9_\-]', '_', text)
    return text[:120]


def escape(text):
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", "")

# Chercheurs (table: author)

def peupler_chercheurs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM author LIMIT {LIMIT}").fetchall()
    total, ok = len(rows), 0
    for i, r in enumerate(rows, 1):
        uri = clean_uri(r["external_id"] or f"author_{r['id']}")
        nom = escape(r["full_name"])
        orcid = r["orcid"] or ""
        pub_count = r["publication_count"] or 0

        query = f"""
        INSERT {{
            :{uri} a :Chercheur ;
                :aPourNom "{nom}" ;
                :aPourId "{escape(r['external_id'] or '')}" ;
                :nbDePublications {pub_count} .
            {":" + uri + ' :aPourOrcid "' + escape(orcid) + '" .' if orcid else ""}
        }}
        WHERE {{ FILTER NOT EXISTS {{ :{uri} a :Chercheur }} }}
        """
        if sparql_update(query):
            ok += 1
        if i % 10 == 0:
            print(f"  → {i}/{total} auteurs traités")
            #time.sleep(0.1)
    conn.close()
    print(f"Auteurs : {ok}/{total}")


# ENTITÉS (table: entity) — institutions + entreprises

def peupler_entites():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM entity LIMIT {LIMIT}").fetchall()
    total, ok = len(rows), 0

    for i, r in enumerate(rows, 1):
        uri = clean_uri(r["external_id"] or r["ror"] or f"entity_{r['id']}")
        nom = escape(r["display_name"] or r["name"])
        etype = (r["type"] or "").lower()
        country = r["country_code"] or ""
        city = r["city"] or ""
        ror = r["ror"] or ""
        website = r["website"] or ""
        description = escape((r["description"] or "")[:500])
        founded = r["founded_date"] or ""
        operating = r["operating_status"] or ""
        funding = r["total_funding"]
        valuation = r["valuation"]
        cited = r["cited_by_count"] or 0
        works = r["works_count"] or 0
        is_ai = r["is_ai_related"]
        ai_pct = r["ai_focus_percent"]

        # Choisir la classe ontologique
        if etype in ("company", "startup"):
            classe = "Entreprise"
        elif etype in ("education", "facility", "government", "nonprofit", "archive"):
            classe = "Université"
        else:
            classe = "Organisation"

        pays_uri = clean_uri(country) if country else None

        extras = ""
        if ror:
            extras += f':{uri} :aPourROR "{escape(ror)}" .\n'
        if website:
            extras += f':{uri} :siteWeb "{escape(website)}" .\n'
        if description:
            extras += f':{uri} :description "{description}" .\n'
        if city:
            extras += f':{uri} :ville "{escape(city)}" .\n'
        if founded:
            extras += f':{uri} :dateDeCreation "{escape(founded)}" .\n'
        if operating:
            extras += f':{uri} :secteur "{escape(operating)}" .\n'
        if funding is not None:
            extras += f':{uri} :totalFunding {funding} .\n'
        if valuation is not None:
            extras += f':{uri} :valuation {valuation} .\n'
        if is_ai is not None:
            extras += f':{uri} :lieAlIA {"true" if is_ai else "false"} .\n'
        if ai_pct is not None:
            extras += f':{uri} :aiFocusPercent {ai_pct} .\n'
        if works:
            extras += f':{uri} :nbDePublications {works} .\n'
        if cited:
            extras += f':{uri} :nbCitations {cited} .\n'

        query = f"""
        INSERT {{
            :{uri} a :{classe} ;
                :aPourNomOrganisation "{nom}" ;
                :typeOrganisation "{escape(etype)}" .
            {f':{uri} :estLocaliseEn :pays_{pays_uri} . :pays_{pays_uri} a :Pays ; :codePays "{country}" .' if pays_uri else ""}
            {extras}
        }}
        WHERE {{ FILTER NOT EXISTS {{ :{uri} a :{classe} }} }}
        """
        if sparql_update(query):
            ok += 1
        if i % 10 == 0:
            print(f"  → {i}/{total} entités traitées")
            time.sleep(0.1)
    conn.close()
    print(f"Entités : {ok}/{total}")


# ARTICLES (table: researchitem)

def peupler_articles():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM researchitem LIMIT {LIMIT}").fetchall()
    total, ok = len(rows), 0

    for i, r in enumerate(rows, 1):
        uri = clean_uri(r["external_id"] or f"article_{r['id']}")
        titre = escape((r["title"] or "")[:300])
        doi = escape(r["doi"] or "")
        abstract = escape((r["abstract"] or "")[:500])
        year = r["year"]
        pub_date = r["publication_date"] or ""
        lang = r["language"] or ""
        citations = r["citation_count"] or 0
        item_type = escape(r["type"] or "")
        is_oa = r["is_open_access"]

        extras = ""
        if doi:
            extras += f':{uri} :aPourDOI "{doi}" .\n'
        if abstract:
            extras += f':{uri} :resume "{abstract}" .\n'
        if lang:
            extras += f':{uri} :langue "{lang}" .\n'
        if year:
            extras += f':{uri} :annee "{year}"^^xsd:gYear .\n'
        if item_type:
            extras += f':{uri} :type "{item_type}" .\n'
        if pub_date and len(str(pub_date)) >= 10:
            extras += f':{uri} :dateDePublication "{str(pub_date)[:10]}"^^xsd:date .\n'
        if is_oa is not None:
            extras += f':{uri} :openAccess {"true" if is_oa else "false"} .\n'

        query = f"""
        INSERT {{
            :{uri} a :TravailDeRecherche ;
                :titre "{titre}" ;
                :nbCitations {citations} ;
                :aPourIdRessource "{escape(r['external_id'] or '')}" .
            {extras}
        }}
        WHERE {{ FILTER NOT EXISTS {{ :{uri} a :TravailDeRecherche }} }}
        """
        if sparql_update(query):
            ok += 1
        if i % 10 == 0:
            print(f"  → {i}/{total} articles traités")
            time.sleep(0.1)
    conn.close()
    print(f"Articles : {ok}/{total}")


# AFFILIATIONS (table: affiliation)
# Relie auteurs ↔ articles ↔ entités

def peupler_affiliations():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # On fait un JOIN pour récupérer les external_id nécessaires
    query_sql = f"""
        SELECT 
            a.author_external_id,
            a.research_item_doi,
            a.entity_ror,
            a.role,
            r.external_id AS research_external_id,
            e.external_id AS entity_external_id
        FROM affiliation a
        LEFT JOIN researchitem r ON a.research_item_id = r.id
        LEFT JOIN entity e ON a.entity_id = e.id
        LIMIT {LIMIT}
    """

    rows = conn.execute(query_sql).fetchall()
    total, ok = len(rows), 0

    for i, r in enumerate(rows, 1):
        auteur_uri = clean_uri(r["author_external_id"])
        article_uri = clean_uri(r["research_external_id"])
        entity_uri = clean_uri(
            r["entity_external_id"] or r["entity_ror"]
        ) if (r["entity_external_id"] or r["entity_ror"]) else None

        role = escape(r["role"] or "")

        triples = f":{auteur_uri} :aEcrit :{article_uri} .\n"
        triples += f":{article_uri} :ecritPar :{auteur_uri} .\n"

        if entity_uri:
            triples += f":{auteur_uri} :estAffilieA :{entity_uri} .\n"

        if role:
            triples += f':{auteur_uri} :role "{role}" .\n'

        sparql = f"INSERT DATA {{ {triples} }}"
        if sparql_update(sparql):
            ok += 1
        if i % 10 == 0:
            print(f"  → {i}/{total} affiliations traitées")
            time.sleep(0.1)
    conn.close()
    print(f"Affiliations : {ok}/{total}")


def compter_triples():
    r = requests.get(
        f"{GRAPHDB_URL}/repositories/{REPO_ID}",
        headers={"Accept": "application/sparql-results+json"},
        params={"query": "SELECT (COUNT(*) AS ?c) WHERE { ?s ?p ?o }"}
    )
    count = r.json()["results"]["bindings"][0]["c"]["value"]
    print(f"\n📊 Total triples : {count}")


if __name__ == "__main__":
    print(f"Peuplement de GraphDB (LIMIT={LIMIT})...\n")

    print("Auteurs...")
    peupler_chercheurs()
    print("✅ Auteurs OK\n")

    print("Entités (institutions + entreprises)...")
    peupler_entites()
    print("✅ Entités OK\n")

    print("Articles...")
    peupler_articles()
    print("✅ Articles OK\n")

    print("Affiliations...")
    peupler_affiliations()
    print("✅ Affiliations OK\n")

    compter_triples()
    print("\n✅ Terminé !")
