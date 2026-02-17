from rdflib import Graph

g = Graph()
g.parse("ontologie/onto_peuplee.ttl", format="turtle")

requete_geo = """
PREFIX : <http://www.semanticweb.org/s2b/ontologie#>
SELECT ?nomAuteur ?nomOrg
WHERE {
    ?auteur :aPourNom ?nomAuteur ;
            :estAffilieA ?org .
    ?org :aPourNom ?nomOrg .
}
LIMIT 10
"""

print(f"{'AUTEUR':<25} | {'ORGANISATION':<30} | {'PAYS'}")
print("-" * 80)

resultats = g.query(requete_geo)
for ligne in resultats:
    print(f"{str(ligne.nomAuteur):<25} | {str(ligne.nomOrganisation):<30} | {str(ligne.nomPays)}")

if len(resultats) == 0:
    print("Aucun résultat. Vérifiez que les organisations et les pays sont bien peuplés.")