from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import XSD
from sqlmodel import Session, select, create_engine
import sys
import os

# Configuration des chemins pour importer vos modèles
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.author import Author
from models.research_item import ResearchItem
from models.affiliation import Affiliation
from models.organization import Organization

# Connexion à la base
engine = create_engine("sqlite:///database.db")
BASE_URI = Namespace("http://www.semanticweb.org/s2b/ontologie#")

def peupler_ontologie():
    g = Graph()
    # Chargement de la structure de base
    g.parse("ontologie/onto_v1.ttl", format="turtle")
    
    with Session(engine) as session:
        # 1. Mapping des articles (ResearchItem)
        articles = session.exec(select(ResearchItem)).all()
        for art in articles:
            art_uri = URIRef(BASE_URI[f"article_{art.id}"])
            g.add((art_uri, RDF.type, BASE_URI.TravailDeRecherche))
            
            # Titre
            if art.title:
                g.add((art_uri, BASE_URI.aPourTitre, Literal(art.title, datatype=XSD.string)))
            
            # Citations
            g.add((art_uri, BASE_URI.aPourScoreCitation, Literal(art.citation_count or 0, datatype=XSD.integer)))
            
            # Domaines (Topics)
            if art.topics:
                # Si topics est une liste (cas SQLModel + JSON)
                for topic in art.topics:
                    topic_clean = topic.lower().replace(" ", "_").replace(".", "_")
                    topic_uri = URIRef(BASE_URI[f"domaine_{topic_clean}"])
                    g.add((topic_uri, RDF.type, BASE_URI.DomaineScientifique))
                    g.add((art_uri, BASE_URI.concerneLeDomaine, topic_uri))

        # 2. Mapping des auteurs (Author)
        auteurs = session.exec(select(Author)).all()
        for aut in auteurs:
            aut_uri = URIRef(BASE_URI[f"chercheur_{aut.id}"])
            g.add((aut_uri, RDF.type, BASE_URI.Chercheur))
            
            if aut.full_name:
                g.add((aut_uri, BASE_URI.aPourNom, Literal(aut.full_name, datatype=XSD.string)))

        # 3. Mapping des liens (Affiliations)
        affiliations = session.exec(select(Affiliation)).all()
        for aff in affiliations:
            aut_uri = URIRef(BASE_URI[f"chercheur_{aff.author_id}"])
            art_uri = URIRef(BASE_URI[f"article_{aff.research_item_id}"])
            
            # Création du lien auteur -> article
            g.add((aut_uri, BASE_URI.aEcrit, art_uri))
            
            # Si une organisation est liée
            if aff.organization_id:
                org_uri = URIRef(BASE_URI[f"org_{aff.organization_id}"])
                g.add((aut_uri, BASE_URI.estAffilieA, org_uri))

    # Sauvegarde
    g.serialize(destination="ontologie/onto_peuplee.ttl", format="turtle")
    print(f"Succès : {len(g)} triplets exportés dans onto_peuplee.ttl")

if __name__ == "__main__":
    peupler_ontologie()