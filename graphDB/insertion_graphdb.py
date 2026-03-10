# insertion_graphdb.py
import sqlite3
import requests
import re

GRAPHDB_URL = "http://localhost:7200"
REPO_ID = "fil-rougev2"
DB_PATH = "../database2.db"
PREFIX = "http://www.semanticweb.org/s2b/ontologie#"
LIMIT = 100  # ← change ici pour tester ou tout insérer

import requests
import time

session = requests.Session()

def sparql_update(query):
    full = f"PREFIX : <{PREFIX}>\n{query}"
    try:
        r = session.post(
            f"{GRAPHDB_URL}/repositories/{REPO_ID}/statements",
            headers={"Content-Type": "application/sparql-update"},
            data=full
        )
        if r.status_code == 204:
            return True
        else:
            print(f"❌ {r.status_code} - {r.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("⏳ Pause connexion...")
        time.sleep(5)
        return sparql_update(query)  # retry


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

def peupler_auteurs():
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
    conn.close()
    print(f"Auteurs : {ok}/{total}")

def peupler_institutions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM institution LIMIT {LIMIT}").fetchall()
    total, ok = len(rows), 0
    for i, r in enumerate(rows, 1):
        uri = clean_uri(r["external_id"] or f"inst_{r['id']}")
        nom = escape(r["display_name"])
        country = r["country_code"] or ""
        inst_type = r["type"] or ""
        pays_uri = clean_uri(country) if country else None
        query = f"""
        INSERT {{
            :{uri} a :Université ;
                :aPourNomOrganisation "{nom}" ;
                :typeOrganisation "{escape(inst_type)}" .
            {f':{uri} :estLocaliseEn :pays_{pays_uri} . :pays_{pays_uri} a :Pays ; :codePays "{country}" .' if pays_uri else ""}
        }}
        WHERE {{ FILTER NOT EXISTS {{ :{uri} a :Université }} }}
        """
        if sparql_update(query):
            ok += 1
        if i % 10 == 0:
            print(f"  → {i}/{total} institutions traitées")
    conn.close()
    print(f"Institutions : {ok}/{total}")

def peupler_organisations():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM organization LIMIT {LIMIT}").fetchall()
    total, ok = len(rows), 0
    for i, r in enumerate(rows, 1):
        uri = clean_uri(r["external_id"] or f"org_{r['id']}")
        nom = escape(r["name"])
        org_type = r["type"] or ""
        country = r["country"] or ""
        is_ai = r["is_ai_related"]
        funding = r["total_funding"]
        nb_inv = r["number_of_investors"]
        founded = r["founded_date"] or ""
        secteur = escape(r["operating_status"] or "")
        pays_uri = clean_uri(country) if country else None
        extras = ""
        if funding:
            extras += f':{uri} :totalFunding "{funding}"^^xsd:decimal .\n'
        if nb_inv:
            extras += f":{uri} :nbInvestisseurs {nb_inv} .\n"
        if is_ai is not None:
            extras += f':{uri} :lieAlIA {"true" if is_ai else "false"}^^xsd:boolean .\n'
        if founded:
            try:
                extras += f':{uri} :dateDeCreation "{founded}"^^xsd:date .\n'
            except:
                pass
        query = f"""
        INSERT {{
            :{uri} a :Entreprise ;
                :aPourNomOrganisation "{nom}" ;
                :typeOrganisation "{escape(org_type)}" ;
                :secteur "{secteur}" .
            {f':{uri} :estLocaliseEn :pays_{clean_uri(country)} . :pays_{clean_uri(country)} a :Pays ; :codePays "{country}" .' if pays_uri else ""}
            {extras}
        }}
        WHERE {{ FILTER NOT EXISTS {{ :{uri} a :Entreprise }} }}
        """
        if sparql_update(query):
            ok += 1
        if i % 10 == 0:
            print(f"  → {i}/{total} organisations traitées")
    conn.close()
    print(f"Organisations : {ok}/{total}")

def peupler_articles():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM researchitem LIMIT {LIMIT}").fetchall()
    total, ok = len(rows), 0
    for i, r in enumerate(rows, 1):
        uri = clean_uri(r["external_id"] or f"article_{r['id']}")
        titre = escape(r["title"] or "")
        doi = escape(r["doi"] or "")
        abstract = escape((r["abstract"] or "")[:500])
        year = r["year"]
        pub_date = r["publication_date"] or ""
        lang = r["language"] or ""
        citations = r["citation_count"] or 0
        item_type = escape(r["type"] or "")
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
    conn.close()
    print(f"Articles : {ok}/{total}")

def peupler_affiliations():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM affiliation LIMIT {LIMIT}").fetchall()
    total, ok = len(rows), 0
    for i, r in enumerate(rows, 1):
        auteur_uri = clean_uri(r["author_external_id"])
        article_uri = clean_uri(r["research_item_external_id"])
        inst_uri = clean_uri(r["institution_external_id"]) if r["institution_external_id"] else None
        triples = f":{auteur_uri} :aEcrit :{article_uri} .\n"
        triples += f":{article_uri} :ecritPar :{auteur_uri} .\n"
        if inst_uri:
            triples += f":{auteur_uri} :estAffilieA :{inst_uri} .\n"
        query = f"INSERT DATA {{ {triples} }}"
        if sparql_update(query):
            ok += 1
        if i % 10 == 0:
            print(f"  → {i}/{total} affiliations traitées")
    conn.close()
    print(f"🔗 Affiliations : {ok}/{total}")

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
    peupler_auteurs()
    print("✅ Auteurs OK\n")
    print("Institutions...")
    #peupler_institutions()
    print("✅ Institutions OK\n")
    print("Organisations...")
    peupler_organisations()
    print("✅ Organisations OK\n")
    print("Articles...")
    peupler_articles()
    print("✅ Articles OK\n")
    print("Affiliations...")
    peupler_affiliations()
    print("✅ Affiliations OK\n")
    compter_triples()
    print("\n✅ Terminé !")
