'''
Fonctionnement:
uv run python -m database.Database_analyse

'''


import json
from sqlmodel import Session, select, create_engine
from models.research_item import ResearchItem
from collections import Counter

# Configuration de l'accès à votre base existante
SQLITE_URL = "sqlite:///database.db"
engine = create_engine(SQLITE_URL)

def profiler_donnees():
    with Session(engine) as session:
        # 1. Récupération de tous les items
        statement = select(ResearchItem)
        items = session.exec(statement).all()
        
        total_items = len(items)
        print(f"--- ANALYSE DE LA BASE ({total_items} notices) ---\n")

        all_org_names = []
        all_org_types = []
        all_countries = []
        company_found = []

        for item in items:
            # On extrait les métriques (stockées en JSON dans la DB)
            metrics = item.metrics if isinstance(item.metrics, dict) else json.loads(item.metrics)
            orgs = metrics.get("organizations", {})
            
            names = orgs.get("names", [])
            types = orgs.get("types", [])
            countries = orgs.get("countries", [])

            all_org_names.extend(names)
            all_org_types.extend(types)
            all_countries.extend(countries)

            # Identification rapide des entreprises
            for n, t in zip(names, types):
                if t == "company" or any(x in n.upper() for x in [" SAS", " SA ", " SARL", " GROUP"]):
                    company_found.append(n)

        # 2. Statistiques sur les Organisations
        name_counts = Counter(all_org_names)
        type_counts = Counter(all_org_types)
        country_counts = Counter(all_countries)
        company_counts = Counter(company_found)

        print("### TOP 10 DES ORGANISATIONS (Toutes catégories)")
        for name, count in name_counts.most_common(10):
            print(f"- {name} : {count} publications")

        print("\n### RÉPARTITION PAR TYPES DE STRUCTURES")
        for t, count in type_counts.items():
            print(f"- {t} : {count}")

        print("\n### TOP 5 DES PAYS")
        for c, count in country_counts.most_common(5):
            print(f"- {c.upper()} : {count}")

        print("\n### FOCUS : ENTREPRISES DÉTECTÉES")
        if not company_counts:
            print("Aucune entreprise identifiée avec certitude.")
        for name, count in company_counts.most_common(10):
            print(f"- [ENTREPRISE] {name} : {count}")

if __name__ == "__main__":
    profiler_donnees()