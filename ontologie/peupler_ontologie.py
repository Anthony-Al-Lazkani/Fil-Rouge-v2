from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import XSD
from sqlmodel import Session, select

# On remonte d'un cran pour atteindre les dossiers models et database
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Maintenant on peut importer vos classes
from models.author import Author
from models.research_item import ResearchItem
from models.affiliation import Affiliation
from models.organization import Organization
from database.initialize import engine  # Vérifiez que l'objet 'engine' est bien dans initialize.py

# 1. Configuration des Espaces de Noms (Namespaces)
# Cela permet de créer des URIs du type http://monsite.fr/chercheur/1
BASE_URI = Namespace("http://www.semanticweb.org/s2b/ontologie#")
g = Graph()

# 2. Chargement de l'ontologie existante
try:
    g.parse("ontologie/onto_v1.ttl", format="turtle")
    print("Ontologie chargée avec succès.")
except Exception as e:
    print(f"Erreur lors du chargement : {e}")

def peupler_base_vers_rdf():
    with Session(engine) as session:
        # --- ÉTAPE A : Les Chercheurs ---
        auteurs = session.exec(select(Author)).all()
        for auteur in auteurs:
            # Création de l'identifiant unique (URI)
            chercheur_uri = URIRef(BASE_URI[f"chercheur_{auteur.id}"])
            
            # Définition du type (Classe Chercheur)
            g.add((chercheur_uri, RDF.type, BASE_URI.Chercheur))
            
            # Ajout du nom (Propriété de donnée)
            if auteur.full_name:
                g.add((chercheur_uri, BASE_URI.aPourNom, Literal(auteur.full_name, datatype=XSD.string)))

        # --- ÉTAPE B : Les Travaux de Recherche ---
        articles = session.exec(select(ResearchItem)).all()
        for art in articles:
            art_uri = URIRef(BASE_URI[f"article_{art.id}"])
            g.add((art_uri, RDF.type, BASE_URI.TravailDeRecherche))
            
            if art.title:
                g.add((art_uri, BASE_URI.aPourTitre, Literal(art.title, datatype=XSD.string)))
            if art.citation_count is not None:
                g.add((art_uri, BASE_URI.aPourScoreCitation, Literal(art.citation_count, datatype=XSD.integer)))

        # --- ÉTAPE C : Les Liens (Affiliations) ---
        # C'est ici que l'on crée les relations entre entités
        affiliations = session.exec(select(Affiliation)).all()
        for aff in affiliations:
            chercheur_uri = URIRef(BASE_URI[f"chercheur_{aff.author_id}"])
            article_uri = URIRef(BASE_URI[f"article_{aff.research_item_id}"])
            
            # Relation : Le chercheur a écrit l'article
            g.add((chercheur_uri, BASE_URI.aEcrit, article_uri))
            
            # Si une organisation est liée
            if aff.organization_id:
                org_uri = URIRef(BASE_URI[f"org_{aff.organization_id}"])
                g.add((org_uri, RDF.type, BASE_URI.Organisation))
                g.add((chercheur_uri, BASE_URI.estAffilieA, org_uri))

    # 3. Sauvegarde du résultat
    g.serialize(destination="ontologie/onto_peuplee.ttl", format="turtle")
    print(f"Peuplement terminé. Fichier 'onto_peuplee.ttl' généré avec {len(g)} triplets.")

if __name__ == "__main__":
    peupler_base_vers_rdf()