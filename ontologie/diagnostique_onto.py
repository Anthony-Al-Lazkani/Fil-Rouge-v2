from rdflib import Graph

g = Graph()
g.parse("ontologie/onto_peuplee_v2.ttl", format="turtle")

# Requête simplifiée au maximum pour voir ce qui existe vraiment
requete_verite = """
SELECT ?type (COUNT(?s) AS ?nb)
WHERE {
    ?s a ?type .
}
GROUP BY ?type
ORDER BY DESC(?nb)
"""

print(f"{'TYPE TROUVÉ DANS LE GRAPHE':<60} | {'NB ENTITÉS'}")
print("-" * 80)

resultats = g.query(requete_verite)
for ligne in resultats:
    print(f"{str(ligne.type):<60} | {ligne.nb}")