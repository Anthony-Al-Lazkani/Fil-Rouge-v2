from rdflib import Graph

g = Graph()
g.parse("ontologie/onto_peuplee.ttl", format="turtle")

print(f"Nombre de triplets chargés : {len(g)}")

# 1. Vérifier les types d'objets présents
print("\n--- 5 premiers types d'objets trouvés ---")
query_types = "SELECT DISTINCT ?type WHERE { ?s a ?type } LIMIT 5"
for row in g.query(query_types):
    print(f"Type trouvé : {row.type}")

# 2. Vérifier les relations (Prédicats) utilisées
print("\n--- 5 premières relations (prédicats) trouvées ---")
query_preds = "SELECT DISTINCT ?p WHERE { ?s ?p ?o } LIMIT 5"
for row in g.query(query_preds):
    print(f"Relation trouvée : {row.p}")