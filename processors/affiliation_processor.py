"""
Processeur de liaison pour la création des affiliations.

Features:
- Analyse les données brutes (champ raw) de ResearchItem.
- Réconcilie les entités via external_id ou ROR.
- Crée les liens dans la table Affiliation sans redondance textuelle.
"""

from sqlmodel import Session, select
from database import engine
from models import ResearchItem, Entity, Affiliation

class AffiliationProcessor:
    def __init__(self):
        # On ouvre une session propre
        self.session = Session(engine)

    def find_entity(self, external_id: str = None, ror: str = None):
        """Recherche une entité existante pour éviter les doublons de liaison."""
        if external_id:
            # Nettoyage des préfixes pour correspondre au stockage épuré
            ext_id = external_id.replace("https://openalex.org/", "")
            entity = self.session.exec(
                select(Entity).where(Entity.external_id == ext_id)
            ).first()
            if entity: return entity

        if ror:
            ror_clean = ror.replace("https://ror.org/", "")
            return self.session.exec(
                select(Entity).where(Entity.ror == ror_clean)
            ).first()
        return None

    def process_research_item(self, item: ResearchItem):
        """Extrait les affiliations depuis le champ raw d'un article."""
        # On utilise 'raw' car 'metrics' a été supprimé
        raw_data = item.raw or {}
        authorships = raw_data.get("authorships", [])
        created_count = 0

        for auth in authorships:
            author_info = auth.get("author", {})
            author_ext_id = author_info.get("id")
            
            # Récupération des institutions liées dans le JSON brut
            institutions = auth.get("institutions", [])
            
            # Détermination du rôle
            role = "first_author" if auth.get("author_position") == "first" else "co_author"
            if auth.get("is_corresponding"):
                role = "corresponding_author"

            # Si aucune institution n'est listée, on crée une affiliation sans entity_id
            if not institutions:
                institutions = [None]

            for inst in institutions:
                entity_id = None
                entity_ror = None
                
                if inst:
                    found = self.find_entity(external_id=inst.get("id"), ror=inst.get("ror"))
                    if found:
                        entity_id = found.id
                        entity_ror = found.ror

                # Création de l'objet Affiliation épuré
                new_aff = Affiliation(
                    research_item_id=item.id,
                    entity_id=entity_id,
                    author_external_id=author_ext_id,
                    entity_ror=entity_ror,
                    research_item_doi=item.doi,
                    role=role,
                    source_name=raw_data.get("source", "unknown"),
                    raw_affiliation_data=inst
                )
                
                # Vérification simple pour éviter les doublons d'affiliation exacts
                existing = self.session.exec(
                    select(Affiliation).where(
                        Affiliation.research_item_id == item.id,
                        Affiliation.author_external_id == author_ext_id,
                        Affiliation.entity_id == entity_id
                    )
                ).first()

                if not existing:
                    self.session.add(new_aff)
                    created_count += 1
        
        self.session.commit()
        return created_count

    def process_all_research_items(self):
        """Parcourt la base pour générer les liaisons manquantes."""
        items = self.session.exec(select(ResearchItem)).all()
        total = 0
        for item in items:
            total += self.process_research_item(item)
        return total