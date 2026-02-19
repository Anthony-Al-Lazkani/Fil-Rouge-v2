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
    print(f"Erreur critique : Impossible de charger les modèles. Racine projet : {ROOT_DIR}")
    raise e

# Configuration de la journalisation pour le diagnostic
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION AVEC ONTOLOGIE GENERIQUE ---
CONFIG = {
    "db_url": "sqlite:///database.db",
    "namespace": "http://www.semanticweb.org/s2b/ontologie#",
    "onto_file": "ontologie/onto_v2.ttl", # Utilisation de votre nouvelle ontologie
    "output_file": "ontologie/onto_peuplee_v2.ttl"
}

NS = Namespace(CONFIG["namespace"])

def peupler_robuste():
    g = Graph()
    try:
        g.parse(CONFIG["onto_file"], format="turtle")
    except Exception as e:
        logger.error(f"Impossible de charger l'ontologie v2 : {e}")
        return

    engine = create_engine(CONFIG["db_url"])
    
    with Session(engine) as session:
        
        # 1. TRAITEMENT DES PERSONNES (Chercheurs et Personnes Productrices)
        try:
            authors = session.exec(select(Author)).all()
            for author in authors:
                author_uri = NS[f"chercheur_{author.id}"]
                # Typage multiple selon votre nouveau schéma
                g.add((author_uri, RDF.type, NS.Chercheur))
                g.add((author_uri, RDF.type, NS.PersonneProductrice))
                
                if author.full_name:
                    g.add((author_uri, NS.aPourNom, Literal(author.full_name, datatype=XSD.string)))
        except Exception as e:
            logger.warning(f"Erreur lors du traitement des personnes : {e}")

        # 2. TRAITEMENT DES ORGANISATIONS (Université, Laboratoire, Entreprise)
        try:
            orgs = session.exec(select(Organization)).all()
            for org in orgs:
                org_uri = NS[f"org_{org.id}"]
                
                # Typage dynamique selon la nature de l'organisation
                org_type_raw = str(org.type).lower() if org.type else ""
                if "univ" in org_type_raw:
                    g.add((org_uri, RDF.type, NS.Université))
                elif "lab" in org_type_raw:
                    g.add((org_uri, RDF.type, NS.Laboratoire))
                elif "company" in org_type_raw or "entreprise" in org_type_raw:
                    g.add((org_uri, RDF.type, NS.Entreprise))
                else:
                    g.add((org_uri, RDF.type, NS.Organisation))
                
                if org.name:
                    g.add((org_uri, NS.aPourNom, Literal(org.name, datatype=XSD.string)))
                
                # Géographie
                if org.country:
                    pays_id = org.country.lower().replace(" ", "_")
                    pays_uri = NS[f"pays_{pays_id}"]
                    g.add((pays_uri, RDF.type, NS.Pays))
                    g.add((pays_uri, NS.nomPays, Literal(org.country, datatype=XSD.string)))
                    g.add((org_uri, NS.estLocaliseEn, pays_uri))
        except Exception as e:
            logger.warning(f"Erreur lors du traitement des organisations : {e}")

        # 3. TRAITEMENT DES TRAVAUX DE RECHERCHE
        try:
            items = session.exec(select(ResearchItem)).all()
            for item in items:
                item_uri = NS[f"article_{item.id}"]
                g.add((item_uri, RDF.type, NS.TravailDeRecherche))
                
                if item.title:
                    g.add((item_uri, NS.aPourTitre, Literal(item.title, datatype=XSD.string)))
                
                if item.citation_count is not None:
                    g.add((item_uri, NS.aPourScoreCitation, Literal(item.citation_count, datatype=XSD.integer)))
                
                # Domaines
                topics = getattr(item, "topics", [])
                if topics:
                    for topic in topics:
                        topic_clean = str(topic).lower().replace(" ", "_").replace(".", "_")
                        topic_uri = NS[f"domaine_{topic_clean}"]
                        g.add((topic_uri, RDF.type, NS.Domaine))
                        g.add((item_uri, NS.concerneLeDomaine, topic_uri))
        except Exception as e:
            logger.error(f"Erreur lors du traitement des articles : {e}")

        # 4. RÉTABLISSEMENT DES LIENS (Affiliations et Écriture)
        try:
            affiliations = session.exec(select(Affiliation)).all()
            for aff in affiliations:
                author_uri = NS[f"chercheur_{aff.author_id}"]
                item_uri = NS[f"article_{aff.research_item_id}"]
                
                # Lien sémantique : La personne productrice a écrit le travail
                g.add((author_uri, NS.aEcrit, item_uri))
                
                # Lien d'affiliation vers l'organisation
                if aff.organization_id:
                    org_uri = NS[f"org_{aff.organization_id}"]
                    g.add((author_uri, NS.estAffilieA, org_uri))
        except Exception as e:
            logger.warning(f"Erreur lors du traitement des affiliations : {e}")

    # Exportation finale
    g.serialize(destination=CONFIG["output_file"], format="turtle")
    logger.info(f"Peuplement V2 terminé : {len(g)} triplets exportés.")

if __name__ == "__main__":
    peupler_robuste()