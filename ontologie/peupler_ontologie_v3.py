import logging
import sys
import os
from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import XSD
from sqlmodel import Session, select, create_engine

# --- LOGIQUE DE CHEMIN ROBUSTE ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from models.author import Author
    from models.research_item import ResearchItem
    from models.affiliation import Affiliation
    from models.entity import Entity
except ImportError as e:
    print(
        f"Erreur critique : Impossible de charger les modèles. Racine projet : {ROOT_DIR}"
    )
    raise e

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "db_url": "sqlite:///database.db",
    "namespace": "http://www.semanticweb.org/s2b/ontologie#",
    "onto_file": "ontologie/onto_v2.ttl",
    "output_file": "ontologie/onto_peuplee_v2.ttl",
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
                g.add((author_uri, RDF.type, NS.Chercheur))
                g.add((author_uri, RDF.type, NS.PersonneProductrice))

                if author.full_name:
                    g.add(
                        (
                            author_uri,
                            NS.aPourNom,
                            Literal(author.full_name, datatype=XSD.string),
                        )
                    )
        except Exception as e:
            logger.warning(f"Erreur lors du traitement des personnes : {e}")

        # 2. TRAITEMENT DES ENTITIES (Université, Laboratoire, Entreprise, Institution)
        try:
            entities = session.exec(select(Entity)).all()
            for entity in entities:
                entity_uri = NS[f"entity_{entity.id}"]

                entity_type_raw = (
                    str(entity.entity_type).lower() if entity.entity_type else ""
                )
                if "univ" in entity_type_raw:
                    g.add((entity_uri, RDF.type, NS.Université))
                elif "lab" in entity_type_raw:
                    g.add((entity_uri, RDF.type, NS.Laboratoire))
                elif "company" in entity_type_raw or "entreprise" in entity_type_raw:
                    g.add((entity_uri, RDF.type, NS.Entreprise))
                elif "institution" in entity_type_raw:
                    g.add((entity_uri, RDF.type, NS.Institution))
                else:
                    g.add((entity_uri, RDF.type, NS.Organisation))

                if entity.name:
                    g.add(
                        (
                            entity_uri,
                            NS.aPourNom,
                            Literal(entity.name, datatype=XSD.string),
                        )
                    )

                country = entity.country or entity.country_code
                if country:
                    pays_id = country.lower().replace(" ", "_")
                    pays_uri = NS[f"pays_{pays_id}"]
                    g.add((pays_uri, RDF.type, NS.Pays))
                    g.add((pays_uri, NS.nomPays, Literal(country, datatype=XSD.string)))
                    g.add((entity_uri, NS.estLocaliseEn, pays_uri))
        except Exception as e:
            logger.warning(f"Erreur lors du traitement des entities : {e}")

        # 3. TRAITEMENT DES TRAVAUX DE RECHERCHE
        try:
            items = session.exec(select(ResearchItem)).all()
            for item in items:
                item_uri = NS[f"article_{item.id}"]
                g.add((item_uri, RDF.type, NS.TravailDeRecherche))

                if item.title:
                    g.add(
                        (
                            item_uri,
                            NS.aPourTitre,
                            Literal(item.title, datatype=XSD.string),
                        )
                    )

                if item.citation_count is not None:
                    g.add(
                        (
                            item_uri,
                            NS.aPourScoreCitation,
                            Literal(item.citation_count, datatype=XSD.integer),
                        )
                    )

                topics = getattr(item, "topics", [])
                if topics:
                    for topic in topics:
                        topic_clean = (
                            str(topic).lower().replace(" ", "_").replace(".", "_")
                        )
                        topic_uri = NS[f"domaine_{topic_clean}"]
                        g.add((topic_uri, RDF.type, NS.Domaine))
                        g.add((item_uri, NS.concerneLeDomaine, topic_uri))
        except Exception as e:
            logger.error(f"Erreur lors du traitement des articles : {e}")

        # 4. RÉTABLISSEMENT DES LIENS (Affiliations et Écriture)
        try:
            affiliations = session.exec(select(Affiliation)).all()
            for aff in affiliations:
                author_uri = NS[f"chercheur_{aff.author_external_id}"]
                item_uri = NS[f"article_{aff.research_item_id}"]

                g.add((author_uri, NS.aEcrit, item_uri))

                if aff.entity_id:
                    entity_uri = NS[f"entity_{aff.entity_id}"]
                    g.add((author_uri, NS.estAffilieA, entity_uri))
        except Exception as e:
            logger.warning(f"Erreur lors du traitement des affiliations : {e}")

    g.serialize(destination=CONFIG["output_file"], format="turtle")
    logger.info(f"Peuplement V2 terminé : {len(g)} triplets exportés.")


if __name__ == "__main__":
    peupler_robuste()
