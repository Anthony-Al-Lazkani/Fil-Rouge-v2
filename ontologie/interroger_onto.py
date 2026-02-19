from rdflib import Graph

g = Graph()
g.parse("ontologie/onto_peuplee_v2.ttl", format="turtle")

# Requête pour lister les articles, leurs domaines et le pays (si disponible)
requete_top_domaines = """
PREFIX : <http://www.semanticweb.org/s2b/ontologie#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?nomDomaine (COUNT(?art) AS ?nbArticles)
WHERE {
    ?art rdf:type :TravailDeRecherche ;
         :concerneLeDomaine ?domaine .
    
    # Nettoyage du nom du domaine
    BIND(REPLACE(STR(?domaine), "^.*#domaine_", "") AS ?nomDomaine)
}
GROUP BY ?nomDomaine
ORDER BY DESC(?nbArticles)
LIMIT 10
"""

print(f"{'DOMAINE SCIENTIFIQUE':<45} | {'NOMBRE D\'ARTICLES'}")
print("-" * 70)

resultats = g.query(requete_top_domaines)
for ligne in resultats:
    # On remplace les underscores par des espaces pour le rendu final
    domaine_propre = str(ligne.nomDomaine).replace("_", " ")
    print(f"{domaine_propre:<45} | {ligne.nbArticles}")