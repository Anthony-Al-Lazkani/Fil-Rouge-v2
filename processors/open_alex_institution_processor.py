"""
Processeur dédié aux institutions OpenAlex.
Remplit la table Entity avec les métadonnées académiques mondiales.
"""
from sqlmodel import Session, select
from models import Entity, Source

class OpenAlexInstitutionProcessor:
    def __init__(self, session: Session):
        self.session = session
        # Initialisation de la source spécifique
        source = self.session.exec(select(Source).where(Source.name == "openalex")).first()
        if not source:
            source = Source(name="openalex", type="academic", base_url="https://openalex.org/")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    def process_institutions(self, institutions: list) -> int:
        """Traite les dictionnaires issus du crawler OpenAlex Institutions."""
        count = 0
        for inst in institutions:
            ext_id = inst.get("external_id")
            ror = inst.get("ror")

            if not ext_id: continue

            # Déduplication par ID ou ROR
            existing = None
            if ror:
                existing = self.session.exec(select(Entity).where(Entity.ror == ror)).first()
            if not existing:
                existing = self.session.exec(select(Entity).where(Entity.external_id == ext_id)).first()

            if existing: continue

            # 1. Préparation des données Géo (en amont pour plus de clarté)
            raw_data = inst.get("raw", {})
            geo = raw_data.get("geo", {})
            # On prend la ville la plus précise disponible
            city_name = inst.get("city") or geo.get("city")

            # 2. Extraction des rôles (Funder/Publisher) pour ton ontologie
            roles_list = raw_data.get("roles", [])
            funder_id = next((r.get("id") for r in roles_list if r.get("role") == "funder"), None)

            # 3. Extraction du domaine pour les futures liaisons par email
            website = inst.get("homepage_url")
            domain = None
            if website:
                # Nettoyage simple : extrait 'washington.edu' de 'https://www.washington.edu'
                domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
            
            # --- EXTRACTION DES TOPICS (Mapping vers Industries) ---
            topics_data = raw_data.get("topics", [])
            # On récupère les display_name des topics, subfields et fields pour couvrir large
            topics_list = []
            for t in topics_data:
                topics_list.append(t.get("display_name"))
                if "subfield" in t:
                    topics_list.append(t["subfield"].get("display_name"))
                if "field" in t:
                    topics_list.append(t["field"].get("display_name"))
            
            # Déduplication et nettoyage
            unique_topics = list(set(filter(None, topics_list)))

            # Vérification automatique de la spécificité IA via les topics
            is_ai = any("artificial intelligence" in s.lower() for s in unique_topics)

            # --- VALORISATION ACADÉMIQUE ---
            summary = raw_data.get("summary_stats", {})
            h_index = summary.get("h_index", 0)
            i10_index = summary.get("i10_index", 0)

            # Création de l'entité
            new_entity = Entity(
                source_id=self.source_id,
                external_id=ext_id,
                ror=ror,
                name=inst.get("display_name", "Unknown"),
                display_name=inst.get("display_name"),
                acronyms=inst.get("acronyms", []),
                type=inst.get("type"),
                country_code=inst.get("country_code"),
                city=city_name,
                website=website,
                industries=unique_topics, # Injection des topics OpenAlex ici
                is_ai_related=is_ai or inst.get("is_ai_related"), # Double check IA
                works_count=inst.get("works_count", 0),
                cited_by_count=inst.get("cited_by_count", 0),
                raw={
                    **inst,
                    "_funder_id": funder_id,
                    "_h_index": h_index,       # Valorisation de l'impact
                    "_i10_index": i10_index,   # Valorisation de la régularité
                    "_email_domain": domain
                }
            )
            
            self.session.add(new_entity)
            count += 1
            
        # Flush pour garantir que tous les IDs techniques sont générés
        self.session.flush()



        # ÉTAPE 2 : Résolution de la hiérarchie (Parent/Child)  --- pour prendre en compte les métadonnées d'affiliations des entités.
        for inst in institutions:
            self._resolve_hierarchy(inst)

        self.session.commit()
        return count

    def _get_existing_entity(self, ext_id, ror):
        """Recherche une entité par ROR ou external_id."""
        if ror:
            res = self.session.exec(select(Entity).where(Entity.ror == ror)).first()
            if res: return res
        return self.session.exec(select(Entity).where(Entity.external_id == ext_id)).first()

    def _resolve_hierarchy(self, inst_data):
        """Définit le parent_id si une relation 'child' est détectée dans OpenAlex."""
        raw = inst_data.get("raw", {})
        associated = raw.get("associated_institutions", [])
        
        # Si cette institution est un 'child', on cherche son 'parent'
        for assoc in associated:
            if assoc.get("relationship") == "parent":
                parent_ext_id = assoc.get("id").split("/")[-1] # Extrait 'I19820366'
                parent_ror = assoc.get("ror")
                
                # On cherche le parent en base
                parent = self._get_existing_entity(parent_ext_id, parent_ror)
                
                if parent:
                    # On cherche l'enfant actuel en base
                    child = self._get_existing_entity(inst_data["external_id"], inst_data.get("ror"))
                    if child and child.id != parent.id:
                        child.parent_id = parent.id
                        self.session.add(child)