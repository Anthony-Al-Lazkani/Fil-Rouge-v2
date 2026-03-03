import logging
import sys
import os
from collections import defaultdict

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
    "onto_file": "ontologie/onto_v3.ttl",
    "output_file": "ontologie/onto_peuplee_v3.ttl"
}

NS = Namespace(CONFIG["namespace"])


def slugify(text: str) -> str:
    """Nettoie une chaîne pour l'utiliser dans une URI."""
    return str(text).lower().strip().replace(" ", "_").replace(".", "_").replace("/", "_")

def peupler_robuste():
    g = Graph()
    try:
        g.parse(CONFIG["onto_file"], format="turtle")
        logger.info("Ontologie chargée avec succès.")
    except Exception as e:
        logger.error(f"Impossible de charger l'ontologie v3 : {e}")
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
                g.add((author_uri, RDF.type, NS.Personne))
                
                if author.full_name:
                    g.add((author_uri, NS.aPourNom, Literal(author.full_name, datatype=XSD.string)))

                # Chercheur : aPourId (external_id = OpenAlex, HAL, etc.)
                if author.external_id:
                    g.add((author_uri, NS.aPourId,
                           Literal(author.external_id, datatype=XSD.string)))

                # Chercheur : aPourOrcid
                if author.orcid:
                    g.add((author_uri, NS.aPourOrcid,
                           Literal(author.orcid, datatype=XSD.string)))

                # Chercheur : nbDePublications
                if author.publication_count is not None:
                    g.add((author_uri, NS.nbDePublications,
                           Literal(author.publication_count, datatype=XSD.integer)))
        except Exception as e:
            logger.warning(f"Erreur lors du traitement des personnes : {e}")

        # 2. TRAITEMENT DES ORGANISATIONS (Université, Laboratoire, Entreprise)
        try:
            orgs = session.exec(select(Organization)).all()
            logger.info(f"{len(orgs)} organisations trouvées.")
            for org in orgs:
                org_uri = NS[f"org_{org.id}"]
                
                # Typage dynamique selon la nature de l'organisation
                org_type_raw = str(org.type).lower() if org.type else ""
                if "univ" in org_type_raw or "education" in org_type_raw:
                    g.add((org_uri, RDF.type, NS.Université))
                elif "lab" in org_type_raw:
                    g.add((org_uri, RDF.type, NS.Laboratoire))
                elif "company" in org_type_raw or "entreprise" in org_type_raw:
                    g.add((org_uri, RDF.type, NS.Entreprise))
                elif "startup" in org_type_raw:
                    g.add((org_uri, RDF.type, NS.Startup))
                else:
                    g.add((org_uri, RDF.type, NS.Organisation))
                
                # --- Data properties Organisation ---
                if org.name:
                    g.add((org_uri, NS.aPourNomOrganisation,
                           Literal(org.clean_name, datatype=XSD.string)))

                if org.type:
                    g.add((org_uri, NS.typeOrganisation,
                           Literal(org.type, datatype=XSD.string)))

                if org.founded_date:
                    g.add((org_uri, NS.dateDeCreation,
                           Literal(org.founded_date, datatype=XSD.string)))

                # --- Data properties Entreprise ---
                # secteur : on utilise industries (liste JSON)
                if org.industries:
                    for industry in org.industries:
                        if industry:
                            g.add((org_uri, NS.secteur,
                                   Literal(str(industry), datatype=XSD.string)))

                if org.is_ai_related is not None:
                    g.add((org_uri, NS.lieAlIA,
                           Literal(org.is_ai_related, datatype=XSD.boolean)))

                if org.number_of_investors is not None:
                    g.add((org_uri, NS.nbInvestisseurs,
                           Literal(org.number_of_investors, datatype=XSD.integer)))

                if org.total_funding is not None:
                    g.add((org_uri, NS.totalFunding,
                           Literal(org.total_funding, datatype=XSD.decimal)))

                # Géographie
                if org.country:
                    pays_id = org.country.lower().replace(" ", "_")
                    pays_uri = NS[f"pays_{pays_id}"]
                    g.add((pays_uri, RDF.type, NS.Pays))
                    g.add((pays_uri, NS.codePays, Literal(org.country, datatype=XSD.string)))
                    g.add((org_uri, NS.estLocaliseEn, pays_uri))

                # --- Fondateurs (lien vers Entrepreneur si trouvé) ---
                if org.founders:
                    for founder_name in org.founders:
                        if founder_name:
                            founder_id = slugify(founder_name)
                            founder_uri = NS[f"entrepreneur_{founder_id}"]
                            g.add((founder_uri, RDF.type, NS.Entrepreneur))
                            g.add((founder_uri, NS.aPourNom,
                                   Literal(str(founder_name), datatype=XSD.string)))
                            g.add((founder_uri, NS.aFonde, org_uri))

        except Exception as e:
            logger.warning(f"Erreur lors du traitement des organisations : {e}")

        # 3. TRAITEMENT DES TRAVAUX DE RECHERCHE
        try:
            items = session.exec(select(ResearchItem)).all()
            logger.info(f"{len(items)} travaux de recherche trouvés.")

            for item in items:
                item_uri = NS[f"article_{item.id}"]
                g.add((item_uri, RDF.type, NS.TravailDeRecherche))

                # Data properties TravailDeRecherche
                if item.title:
                    g.add((item_uri, NS.titre,
                           Literal(item.title, datatype=XSD.string)))

                if item.doi:
                    g.add((item_uri, NS.aPourDOI,
                           Literal(item.doi, datatype=XSD.string)))

                if item.abstract:
                    g.add((item_uri, NS.resume,
                           Literal(item.abstract, datatype=XSD.string)))

                if item.citation_count is not None:
                    g.add((item_uri, NS.nbCitations,
                           Literal(item.citation_count, datatype=XSD.integer)))

                if item.language:
                    g.add((item_uri, NS.langue,
                           Literal(item.language, datatype=XSD.string)))

                if item.publication_date:
                    g.add((item_uri, NS.dateDePublication,
                           Literal(item.publication_date.date(), datatype=XSD.date)))

                # Mots-clés (liste JSON)
                if item.keywords:
                    for kw in item.keywords:
                        if kw:
                            g.add((item_uri, NS.motsCles,
                                   Literal(str(kw), datatype=XSD.string)))

                # Data properties RessourceDeConnaissance
                if item.year:
                    g.add((item_uri, NS.annee,
                           Literal(item.year, datatype=XSD.gYear)))

                if item.type:
                    g.add((item_uri, NS.typeRessource,
                           Literal(item.type, datatype=XSD.string)))

                if item.external_id:
                    g.add((item_uri, NS.aPourIdRessource,
                           Literal(item.external_id, datatype=XSD.string)))
                
                # Domaines (topics, liste JSON)
                if item.topics:
                    for topic in item.topics:
                        if topic:
                            topic_uri = NS[f"domaine_{slugify(topic)}"]
                            g.add((topic_uri, RDF.type, NS.Domaine))
                            g.add((topic_uri, NS.aPourNomFR,
                                   Literal(str(topic), datatype=XSD.string)))
                            g.add((topic_uri, NS.aPourNameEN,
                                   Literal(str(topic), datatype=XSD.string)))
                            g.add((item_uri, NS.aPourDomaine, topic_uri))

        except Exception as e:
            logger.error(f"Erreur lors du traitement des articles : {e}")

        # 4. RÉTABLISSEMENT DES LIENS (Affiliations et Écriture)
        try:
            affiliations = session.exec(select(Affiliation)).all()
            logger.info(f"{len(affiliations)} affiliations trouvées.")

            # Index pour la section co-auteurs
            article_authors = defaultdict(list)

            for aff in affiliations:
                author_uri = NS[f"chercheur_{aff.author_id}"]
                item_uri = NS[f"article_{aff.research_item_id}"]
                
                # Lien sémantique : La personne productrice a écrit le travail
                # aEcrit + inverse écritPar
                g.add((author_uri, NS.aEcrit, item_uri))
                g.add((item_uri, NS.ecritPar, author_uri))
                
                # Lien d'affiliation vers l'organisation
                if aff.organization_id:
                    org_uri = NS[f"org_{aff.organization_id}"]
                    g.add((author_uri, NS.estAffilieA, org_uri))

                # Index pour co-auteurs
                article_authors[aff.research_item_id].append(aff.author_id)

        except Exception as e:
            logger.warning(f"Erreur lors du traitement des affiliations : {e}")


        # CO-AUTEURS (aPourCoauteur, symétrique)

        try:
            coauteur_pairs = set()
            for article_id, author_ids in article_authors.items():
                # Dédoublonnage des auteurs par article
                unique_ids = list(set(author_ids))
                for i in range(len(unique_ids)):
                    for j in range(i + 1, len(unique_ids)):
                        pair = tuple(sorted([unique_ids[i], unique_ids[j]]))
                        if pair not in coauteur_pairs:
                            coauteur_pairs.add(pair)
                            a1 = NS[f"chercheur_{pair[0]}"]
                            a2 = NS[f"chercheur_{pair[1]}"]
                            g.add((a1, NS.aPourCoauteur, a2))
                            g.add((a2, NS.aPourCoauteur, a1))

            logger.info(f"{len(coauteur_pairs)} paires de co-auteurs générées.")

        except Exception as e:
            logger.warning(f"Erreur traitement co-auteurs : {e}")

    # Exportation finale
    g.serialize(destination=CONFIG["output_file"], format="turtle")
    logger.info(f"Peuplement V3 terminé : {len(g)} triplets exportés.")

if __name__ == "__main__":
    peupler_robuste()