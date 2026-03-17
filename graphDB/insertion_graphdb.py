"""
À partir de la base de données, peuple l'ontologie dans GraphDB
"""
import json
import sqlite3
from pathlib import Path
import requests
import re
import time

import unicodedata

GRAPHDB_URL = "http://localhost:7200"
REPO_ID = "fil-rougev1"
DB_PATH = Path(__file__).parent.parent / "database.db"
PREFIX = "http://www.semanticweb.org/s2b/ontologie#"
LIMIT = 100000000

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
        print("Pause connexion...")
        time.sleep(5)
        return sparql_update(query)


def clean_uri(text):
    if not text:
        return "unknown"
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.strip().replace(" ", "_").replace("'", "").replace('"', '')
    text = re.sub(r'[^a-zA-Z0-9_\-]', '_', text)
    return text[:120]


def escape(text):
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", "")

# Chercheurs (table: author)

# PERSONNES (table: author)

def peupler_personnes():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM author LIMIT {LIMIT}").fetchall()
    total, ok = len(rows), 0

    for i, r in enumerate(rows, 1):
        uri = clean_uri(r["external_id"] or f"person_{r['id']}")
        nom = escape(r["full_name"])
        orcid = r["orcid"] or ""
        pub_count = r["publication_count"] or 0
        ext_id = escape(r["external_id"] or "")

        extras = ""
        if orcid:
            extras += f':{uri} :aPourOrcid "{escape(orcid)}" .\n'
        if pub_count:
            extras += f':{uri} :nbDePublications {pub_count} .\n'

        query = f"""
        DELETE {{ :{uri} :aPourNom ?old }}
        INSERT {{
            :{uri} a :Personne ;
                :aPourNom "{nom}" ;
                :aPourId "{ext_id}" .
            {extras}
        }}
        WHERE {{ OPTIONAL {{ :{uri} :aPourNom ?old }} }}
        """

        if sparql_update(query):
            ok += 1
        if i % 10 == 0:
            print(f"  → {i}/{total} personnes traitées")

    conn.close()
    print(f"Personnes : {ok}/{total}")


# ENTITÉS (table: entity)

def peupler_entites():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM entity LIMIT {LIMIT}").fetchall()
    total, ok = len(rows), 0

    # Pré-charger tous les parents en une seule requête
    parent_map = {}
    parent_rows = conn.execute("SELECT id, external_id, ror FROM entity WHERE id IN (SELECT DISTINCT parent_id FROM entity WHERE parent_id IS NOT NULL)").fetchall()
    for pr in parent_rows:
        parent_map[pr["id"]] = clean_uri(pr["external_id"] or pr["ror"])

    for i, r in enumerate(rows, 1):
        uri = clean_uri(r["external_id"] or r["ror"] or f"entity_{r['id']}")
        nom = escape(r["display_name"] or r["name"] or "Inconnu")
        etype = (r["type"] or "").lower()
        country = r["country_code"] or ""
        city = r["city"] or ""
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
        revenue = r["estimated_revenue"] or ""
        last_funding = r["last_funding_date"] or ""

        # Industries (JSON list → string)
        industries_raw = r["industries"]
        if industries_raw and isinstance(industries_raw, str):
            try:
                industries_list = json.loads(industries_raw)
            except (json.JSONDecodeError, TypeError):
                industries_list = []
        elif isinstance(industries_raw, list):
            industries_list = industries_raw
        else:
            industries_list = []

        # Acronymes
        acronyms_raw = r["acronyms"]
        if acronyms_raw and isinstance(acronyms_raw, str):
            try:
                acronyms_list = json.loads(acronyms_raw)
            except (json.JSONDecodeError, TypeError):
                acronyms_list = []
        elif isinstance(acronyms_raw, list):
            acronyms_list = acronyms_raw
        else:
            acronyms_list = []

        # Classe ontologique
        if etype == "facility, education":
            classe = ["Laboratoire", "Université"]
        elif etype in ("company", "startup", "entreprise"):
            classe = ["Entreprise"]
        elif etype == "education":
            classe = ["Université"]
        elif etype == "facility":
            classe = ["Laboratoire"]
        elif etype in ("government", "nonprofit", "investor", "archive", "funder"):
            classe = ["OrganisationFacilitatrice"]
        else:
            classe = ["Organisation"]

        # URI pays : remplacer espaces par underscore
        pays_uri = clean_uri(country.replace(" ", "_")) if country else None

        # Parent pré-chargé
        parent_id = r["parent_id"]
        parent_ext = parent_map.get(parent_id) if parent_id else None

        extras = ""
        if website:
            extras += f':{uri} :siteWeb "{escape(website)}" .\n'
        if description:
            extras += f':{uri} :description "{description}" .\n'
        if city:
            extras += f':{uri} :ville "{escape(city)}" .\n'
        if founded:
            extras += f':{uri} :dateDeCreation "{escape(founded)}" .\n'
        if operating:
            extras += f':{uri} :statutOperationnel "{escape(operating)}" .\n'
        if funding is not None:
            extras += f':{uri} :totalFunding "{funding}"^^xsd:decimal .\n'
        if valuation is not None:
            extras += f':{uri} :valuation "{valuation}"^^xsd:decimal .\n'
        if is_ai is not None:
            extras += f':{uri} :lieAlIA {"true" if is_ai else "false"} .\n'
        if ai_pct is not None:
            extras += f':{uri} :aiFocusPercent {ai_pct} .\n'
        if works:
            extras += f':{uri} :nbDePublications {works} .\n'
        if cited:
            extras += f':{uri} :nbCitations {cited} .\n'
        if revenue:
            extras += f':{uri} :estimatedRevenue "{escape(revenue)}" .\n'
        if last_funding:
            extras += f':{uri} :lastFundingDate "{escape(last_funding)}" .\n'
        if parent_ext:
            extras += f':{uri} :estFilialeDe :{parent_ext} .\n'
        for ind in industries_list:
            extras += f':{uri} :secteur "{escape(str(ind))}" .\n'
        for acr in acronyms_list:
            extras += f':{uri} :acronyme "{escape(str(acr))}" .\n'

        types_str = ", ".join(f":{c}" for c in classe)
        query = f"""
        DELETE WHERE {{ :{uri} ?p ?o }} ;
        INSERT DATA {{
            :{uri} a {types_str} ;
                :aPourNomOrganisation "{nom}" ;
                :typeOrganisation "{escape(etype)}" .
            {f':{uri} :estLocaliseEn :pays_{pays_uri} . :pays_{pays_uri} a :Pays ; :codePays "{escape(country)}" .' if pays_uri else ""}
            {extras}
        }}
        """

        if sparql_update(query):
            ok += 1
        if i % 10 == 0:
            print(f"  → {i}/{total} entites traitees")
            time.sleep(0.1)

    conn.close()
    print(f"Entites : {ok}/{total}")

# TravailDeRecherche+Brevet (table: researchitem)

def peupler_researchitem():
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
        license_val = r["license"] or ""
        url = r["url"] or ""
        is_retracted = r["is_retracted"]

        # Keywords & Topics (JSON lists)
        for field_name in ("keywords", "topics"):
            raw = r[field_name]
            if raw and isinstance(raw, str):
                try:
                    locals()[field_name] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    locals()[field_name] = []
            elif isinstance(raw, list):
                locals()[field_name] = raw
            else:
                locals()[field_name] = []

        keywords = locals().get("keywords", [])
        topics = locals().get("topics", [])

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
        if license_val:
            extras += f':{uri} :licence "{escape(license_val)}" .\n'
        if url:
            extras += f':{uri} :url "{escape(url)}" .\n'
        if is_retracted:
            extras += f':{uri} :estRetracte true .\n'

        # Mots-clés → domaines
        for kw in keywords:
            kw_uri = clean_uri(str(kw))
            extras += f':{uri} :aPourDomaine :{kw_uri} .\n'
            extras += f':{kw_uri} a :Domaine ; :aPourNameEN "{escape(str(kw))}" .\n'

        # Topics → domaines
        for tp in topics:
            tp_uri = clean_uri(str(tp))
            extras += f':{uri} :aPourDomaine :{tp_uri} .\n'
            extras += f':{tp_uri} a :Domaine ; :aPourNameEN "{escape(str(tp))}" .\n'

        if item_type == "patent":
            classe = "Brevet"
        else:
            classe = "TravailDeRecherche"

        query = f"""
        DELETE {{ :{uri} :titre ?old ; :nbCitations ?oldCit }}
        INSERT {{
            :{uri} a :{classe} ;
                :titre "{titre}" ;
                :nbCitations {citations} ;
                :aPourIdRessource "{escape(r['external_id'] or '')}" .
            {extras}
        }}
        WHERE {{ OPTIONAL {{ :{uri} :titre ?old ; :nbCitations ?oldCit }} }}
        """

        if sparql_update(query):
            ok += 1
        if i % 10 == 0:
            print(f"  → {i}/{total} articles traités")
            time.sleep(0.1)

    conn.close()
    print(f"Articles : {ok}/{total}")

# AFFILIATIONS (table: affiliation)

def peupler_affiliations():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query_sql = f"""
        SELECT
            a.entity_id,
            a.author_external_id,
            a.research_item_doi,
            a.entity_ror,
            a.role,
            a.source_name,
            r.external_id AS research_external_id,
            r.type AS research_type,
            e.external_id AS entity_external_id,
            e.ror AS entity_ror_resolved
        FROM affiliation a
        LEFT JOIN researchitem r ON a.research_item_id = r.id
        LEFT JOIN entity e ON a.entity_id = e.id
        LIMIT {LIMIT}
    """

    rows = conn.execute(query_sql).fetchall()
    total, ok = len(rows), 0

    for i, r in enumerate(rows, 1):
        auteur_uri = clean_uri(r["author_external_id"])
        article_uri = clean_uri(r["research_external_id"]) if r["research_external_id"] else None
        entity_uri = clean_uri(
            r["entity_external_id"] or r["entity_ror_resolved"] or r["entity_ror"]
        ) if (r["entity_external_id"] or r["entity_ror_resolved"] or r["entity_ror"]) else f"entity_{r['entity_id']}" if \
        r["entity_id"] else None

        role = (r["role"] or "").strip().lower()
        research_type = (r["research_type"] or "").strip().lower()

        triples = []

        # --- Affiliation : toujours si entité ---
        if entity_uri:
            triples.append(f":{auteur_uri} :estAffilieA :{entity_uri} .")

        # --- Rôles ---
        if role == "founder" and entity_uri:
            triples.append(f":{auteur_uri} :aFonde :{entity_uri} .")
        elif role == "leader" and entity_uri:
            triples.append(f":{auteur_uri} :dirige :{entity_uri} .")

        # --- Research items (indépendant du rôle) ---
        if article_uri:
            if research_type in ("brevet", "patent"):
                triples.append(f":{article_uri} :estDeposePar :{auteur_uri} .")
                if entity_uri:
                    triples.append(f":{article_uri} :estDeposePar :{entity_uri} .")
            else:
                triples.append(f":{auteur_uri} :aEcrit :{article_uri} .")
                triples.append(f":{article_uri} :estEcritPar :{auteur_uri} .")

        if not triples:
            continue

        sparql = f"INSERT DATA {{ {chr(10).join(triples)} }}"

        if sparql_update(sparql):
            ok += 1
        if i % 10 == 0:
            print(f"  → {i}/{total} affiliations traitées")
            time.sleep(0.1)

    conn.close()


def compter_triples():
    r = requests.get(
        f"{GRAPHDB_URL}/repositories/{REPO_ID}",
        headers={"Accept": "application/sparql-results+json"},
        params={"query": "SELECT (COUNT(*) AS ?c) WHERE { ?s ?p ?o }"}
    )
    count = r.json()["results"]["bindings"][0]["c"]["value"]
    print(f"\n📊 Total triples : {count}")


if __name__ == "__main__":
    import time as _time
    _start = _time.time()
    print(f"Peuplement de GraphDB (LIMIT={LIMIT})...\n")

    print("Personnes...")
    peupler_personnes()
    print("✅ Personnes OK\n")

    print("Entités (institutions + entreprises)...")
    peupler_entites()
    print("✅ Entités OK\n")

    print("ResearchItems...")
    peupler_researchitem()
    print("✅ ResearchItems OK\n")

    print("Affiliations...")
    peupler_affiliations()
    print("✅ Affiliations OK\n")

    compter_triples()
    elapsed = _time.time() - _start
    minutes, seconds = divmod(int(elapsed), 60)
    print(f"\n✅ Terminé en {minutes}m {seconds}s")
