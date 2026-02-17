import logging
import sys
import os
from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import XSD
from sqlmodel import Session, select, create_engine

# --- LOGIQUE DE CHEMIN ROBUSTE ---
# On récupère le chemin absolu du dossier parent du script (la racine du projet)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Maintenant les imports fonctionneront, peu importe d'où vous lancez le script
try:
    from models.author import Author
    from models.research_item import ResearchItem
    from models.affiliation import Affiliation
    from models.organization import Organization
except ImportError as e:
    print(f"Erreur critique : Impossible de charger les modèles. Vérifiez ROOT_DIR : {ROOT_DIR}")
    raise e

# Configuration de la journalisation pour le diagnostic
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ABSTRAITE ---
CONFIG = {
    "db_url": "sqlite:///database.db",
    "namespace": "http://www.semanticweb.org/s2b/ontologie#",
    "onto_file": "ontologie/onto_v1.ttl",
    "output_file": "ontologie/onto_peuplee.ttl"
}

# Correspondance entre Colonnes SQL et Propriétés RDF
# Si une colonne change de nom, vous ne modifiez que ce dictionnaire
MAPPING = {
    "Author": {"name": "full_name", "type": "Chercheur"},
    "ResearchItem": {"title": "title", "citations": "citation_count", "type": "TravailDeRecherche"}
}

NS = Namespace(CONFIG["namespace"])

def get_safe_attr(obj, attr_name, default=None):
    """Récupère un attribut de manière sécurisée sans faire planter le script."""
    return getattr(obj, attr_name, default)

def peupler_robuste():
    g = Graph()
    try:
        g.parse(CONFIG["onto_file"], format="turtle")
    except Exception as e:
        logger.error(f"Impossible de charger l'ontologie : {e}")
        return

    engine = create_engine(CONFIG["db_url"])
    
    with Session(engine) as session:
        # Traitement des articles
        try:
            from models.research_item import ResearchItem
            items = session.exec(select(ResearchItem)).all()
            for item in items:
                item_uri = NS[f"article_{item.id}"]
                g.add((item_uri, RDF.type, NS.TravailDeRecherche))
                
                # TITRE
                title = getattr(item, "title", None)
                if title:
                    g.add((item_uri, NS.aPourTitre, Literal(title, datatype=XSD.string)))
                
                # CITATIONS
                cits = getattr(item, "citation_count", 0)
                g.add((item_uri, NS.aPourScoreCitation, Literal(cits or 0, datatype=XSD.integer)))
                
                # DOMAINES (Ce qui faisait gonfler le nombre de triplets)
                topics = getattr(item, "topics", [])
                if topics:
                    for topic in topics:
                        topic_clean = str(topic).lower().replace(" ", "_").replace(".", "_")
                        topic_uri = NS[f"domaine_{topic_clean}"]
                        g.add((topic_uri, RDF.type, NS.DomaineScientifique))
                        g.add((item_uri, NS.concerneLeDomaine, topic_uri))
                        
        except Exception as e:
            logger.error(f"Erreur lors du traitement riche des articles : {e}")

        # Traitement générique des auteurs
        try:
            from models.author import Author
            authors = session.exec(select(Author)).all()
            for author in authors:
                author_uri = NS[f"chercheur_{author.id}"]
                g.add((author_uri, RDF.type, NS[MAPPING["Author"]["type"]]))
                
                name = get_safe_attr(author, MAPPING["Author"]["name"])
                if name:
                    g.add((author_uri, NS.aPourNom, Literal(name, datatype=XSD.string)))
        except Exception as e:
            logger.warning(f"Erreur lors du traitement des auteurs : {e}")
        
        # --- TRAITEMENT DES ORGANISATIONS ET GÉOGRAPHIE ---
        try:
            from models.organization import Organization
            orgs = session.exec(select(Organization)).all()
            for org in orgs:
                org_uri = NS[f"org_{org.id}"]
                g.add((org_uri, RDF.type, NS.Organisation))
                
                if org.name:
                    g.add((org_uri, NS.aPourNom, Literal(org.name, datatype=XSD.string)))
                
                # Gestion du Pays
                if org.country:
                    pays_id = org.country.lower().replace(" ", "_")
                    pays_uri = NS[f"pays_{pays_id}"]
                    g.add((pays_uri, RDF.type, NS.Pays))
                    g.add((pays_uri, NS.nomPays, Literal(org.country, datatype=XSD.string)))
                    # Lien Org -> Pays
                    g.add((org_uri, NS.estLocaliseEn, pays_uri))
        except Exception as e:
            logger.warning(f"Erreur lors du traitement des organisations : {e}")

        # --- RÉTABLISSEMENT DES LIENS (Affiliations) ---
        try:
            from models.affiliation import Affiliation
            affiliations = session.exec(select(Affiliation)).all()
            for aff in affiliations:
                author_uri = NS[f"chercheur_{aff.author_id}"]
                item_uri = NS[f"article_{aff.research_item_id}"]
                
                # Lien Auteur -> Article
                g.add((author_uri, NS.aEcrit, item_uri))
                
                # Lien Auteur -> Organisation (Le pont vers la géographie)
                if aff.organization_id:
                    org_uri = NS[f"org_{aff.organization_id}"]
                    g.add((author_uri, NS.estAffilieA, org_uri))
        except Exception as e:
            logger.warning(f"Erreur lors du traitement des affiliations : {e}")

    g.serialize(destination=CONFIG["output_file"], format="turtle")
    logger.info(f"Peuplement terminé : {len(g)} triplets générés.")

if __name__ == "__main__":
    peupler_robuste()