from rdflib import Graph

g = Graph()
g.parse("ontologie/onto_peuplee_v2.ttl", format="turtle")

def executer_analyse(titre, sparql, colonnes):
    print(f"\n=== {titre} ===")
    print("-" * 80)
    resultats = g.query(sparql)
    
    # Entête
    header = " | ".join([f"{col:<30}" for col in colonnes])
    print(header)
    print("-" * 80)
    
    for ligne in resultats:
        print(" | ".join([f"{str(val):<30}" for val in ligne]))
    
    if len(resultats) == 0:
        print("Aucune donnée disponible pour cette analyse.")

# --- 1. Domaines de recherche les plus importants ---
q1 = """
PREFIX : <http://www.semanticweb.org/s2b/ontologie#>
SELECT ?nomDomaine (COUNT(?art) AS ?nbArticles)
WHERE {
    ?art a :TravailDeRecherche ; :concerneLeDomaine ?domaine .
    BIND(REPLACE(STR(?domaine), "^.*#domaine_", "") AS ?nomDomaine)
}
GROUP BY ?nomDomaine ORDER BY DESC(?nbArticles) LIMIT 5
"""

# --- 2. Lien entre articles et brevets ---
q2 = """
PREFIX : <http://www.semanticweb.org/s2b/ontologie#>
SELECT ?titreArticle ?idBrevet
WHERE {
    ?brevet a :Brevet ; :deriveDe ?article .
    ?article :aPourTitre ?titreArticle .
    BIND(REPLACE(STR(?brevet), "^.*#", "") AS ?idBrevet)
}
LIMIT 5
"""

# --- 3. Chercheurs qui publient et déposent des brevets ---
q3 = """
PREFIX : <http://www.semanticweb.org/s2b/ontologie#>
SELECT ?nomChercheur (COUNT(DISTINCT ?art) AS ?nbPublis) (COUNT(DISTINCT ?brevet) AS ?nbBrevets)
WHERE {
    ?c a :Chercheur ; :aPourNom ?nomChercheur ; :aEcrit ?art .
    ?brevet :deposePar ?c .
}
GROUP BY ?nomChercheur ORDER BY DESC(?nbBrevets) LIMIT 5
"""

# --- 4. Pays qui déposent le plus de brevets ---
q4 = """
PREFIX : <http://www.semanticweb.org/s2b/ontologie#>
SELECT ?nomPays (COUNT(?brevet) AS ?nbBrevets)
WHERE {
    ?brevet a :Brevet ; :deposePar ?p .
    ?p :estAffilieA ?org .
    ?org :estLocaliseEn ?pays .
    ?pays :nomPays ?nomPays .
}
GROUP BY ?nomPays ORDER BY DESC(?nbBrevets) LIMIT 5
"""

# --- 5. Pays qui rédigent le plus d'articles ---
q5 = """
PREFIX : <http://www.semanticweb.org/s2b/ontologie#>
SELECT ?nomPays (COUNT(?art) AS ?nbArticles)
WHERE {
    ?art a :TravailDeRecherche .
    ?auteur :aEcrit ?art ; :estAffilieA ?org .
    ?org :estLocaliseEn ?pays .
    ?pays :nomPays ?nomPays .
}
GROUP BY ?nomPays ORDER BY DESC(?nbArticles) LIMIT 5
"""

# Exécution du tableau de bord
executer_analyse("DOMAINES DE RECHERCHE LES PLUS IMPORTANTS", q1, ["Domaine", "Nombre d'articles"])
executer_analyse("LIEN ENTRE ARTICLES ET BREVETS", q2, ["Titre Article", "ID Brevet"])
executer_analyse("CHERCHEURS HYBRIDES (PUBLICATION & BREVET)", q3, ["Chercheur", "Articles", "Brevets"])
executer_analyse("CLASSEMENT GÉOGRAPHIQUE - BREVETS", q4, ["Pays", "Nombre de Brevets"])
executer_analyse("CLASSEMENT GÉOGRAPHIQUE - ARTICLES", q5, ["Pays", "Nombre d'Articles"])