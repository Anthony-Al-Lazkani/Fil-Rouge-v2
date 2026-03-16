"""
Processeur d'ingestion des documents locaux (csv récupérés depuis Crunchbase et Kaggle)

Ce module centralise l'ingestion de données hétérogènes provenant de sources CSV locales (Crunchbase / Kaggle)
Il assure la normalisation financière, l'extraction géographique par scan de contenu 
et la traçabilité des données via le champ 'raw'.

Fonctionnalités clés :
- Unification sous une source unique : 'local_startup_db'.
- Détection robuste des entités : Scan de contenu pour pallier les décalages de colonnes CSV.
- Normalisation monétaire : Conversion automatique des suffixes (K, M, B, T).
- Déduplication : Vérification de l'existence des entités par nom avant insertion.
"""

import csv
from pathlib import Path
from typing import List, Optional
from sqlmodel import Session, select 
from database import engine
from models import Entity, Source, Affiliation, Author

class OrganizationProcessor:
    def __init__(self, session: Session, data_dir: Path):
        self.session = session
        self.data_dir = data_dir
        # Récupère ou crée la source ombrelle unique
        source = self.session.exec(select(Source).where(Source.name == "local_startup_db")).first()
        if not source:
            source = Source(name="local_startup_db", type="business")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    # --- MÉTHODES DE NETTOYAGE ---

    @staticmethod
    def clean_string(s) -> Optional[str]:
        if s is None: return None
        s = str(s).strip()
        if s.lower() in ("n/a", "nan", "", "none", "undisclosed"): return None
        return s

    @staticmethod
    def parse_number(s) -> Optional[float]:
        if s is None: return None
        s = str(s).strip().replace(",", "").replace("$", "").replace(" ", "")
        if not s or s.lower() in ("n/a", "undisclosed"): return None
        multipliers = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}
        for suffix, mult in multipliers.items():
            if suffix in s.lower():
                try: return float(s.lower().replace(suffix, "")) * mult
                except: return None
        try: return float(s)
        except: return None

    @staticmethod
    def parse_industries(industries_str: str) -> List[str]:
        if not industries_str: return []
        return [i.strip() for i in industries_str.split(",")]

    def _safe_add_entity(self, entity: Entity):
        """Vérifie le doublon par nom avant d'ajouter à la session."""
        existing = self.session.exec(select(Entity).where(Entity.name == entity.name)).first()
        if not existing:
            self.session.add(entity)
            return True
        return False
    

    # --- MÉTHODES D'INGESTION ---
    def process_ai_companies(self) -> int:
            """Source 2: AI_Companies (Focus IA avec détection pays correcte)."""
            path = self.data_dir / "AI_Companies.csv"
            if not path.exists(): return 0
            count = 0
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = self.clean_string(row.get("Company_Name"))
                    if not name: continue
                    
                    # --- GESTION GÉOGRAPHIQUE ---
                    loc_raw = row.get("Location", "")
                    city = None
                    country_code = None
                    
                    if loc_raw and "," in loc_raw:
                        parts = [p.strip() for p in loc_raw.split(",")]
                        city = parts[0]
                        last_part = parts[-1]
                        
                        # Si la dernière partie fait 2 caractères (CA, TX, FL...), c'est un État US
                        if len(last_part) == 2 and last_part.isupper():
                            country_code = "USA"
                        else:
                            # Sinon on prend le nom du pays (Estonia, Poland, Pakistan...)
                            country_code = last_part
                    
                    # --- VALUATION (Minimum Project Size) ---
                    proj_size_raw = row.get("Minimum Project Size", "")
                    valuation = None
                    if proj_size_raw and proj_size_raw not in ("Undisclosed", ""):
                        try:
                            # On retire "$", "," et "+" pour ne garder que le nombre
                            clean_val = proj_size_raw.replace("$", "").replace(",", "").replace("+", "").strip()
                            valuation = float(clean_val)
                        except (ValueError, TypeError):
                            valuation = None


                    
                    # --- FOCUS IA ---
                    ai_focus_raw = self.clean_string(row.get("Percent AI Service Focus"))
                    ai_focus = None
                    if ai_focus_raw:
                        try:
                            clean_val = ai_focus_raw.replace("%", "").split("-")[0].strip()
                            ai_focus = int(float(clean_val))
                        except (ValueError, TypeError):
                            ai_focus = None

                    entity = Entity(
                        source_id=self.source_id,
                        name=name,
                        type="company",
                        website=self.clean_string(row.get("Website")),
                        city=city,
                        country_code=country_code,
                        ai_focus_percent=ai_focus,
                        valuation=valuation,
                        is_ai_related=True,
                        raw={**row, "_extraction_source": "ai_companies"}
                    )
                    if self._safe_add_entity(entity): 
                        count += 1
                        
            self.session.commit()
            return count


    def process_startups_2021(self) -> int:
        """Source 4: Startups-in-2021-end.csv (Entreprises + Investisseurs en métadonnées)."""
        import re
        path = self.data_dir / "Startups-in-2021-end.csv"
        if not path.exists(): return 0
        count = 0

        def extract_year(s) -> Optional[str]:
            if not s: return None
            # Utilisation d'une raw string pour éviter le SyntaxWarning sur \d
            match = re.search(r'\b(19|20)\d{2}\b', str(s))
            return match.group(0) if match else None

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = self.clean_string(row.get("Company"))
                if not name: continue
                
                # 1. VALUATION
                val_raw = row.get("Valuation ($B)", "0").replace("$", "")
                try:
                    valuation = float(val_raw) * 1_000_000_000
                except:
                    valuation = None

                # 2. CRÉATION DE L'ENTITÉ (L'entreprise)
                entity = Entity(
                    source_id=self.source_id,
                    name=name,
                    type="company",
                    valuation=valuation,
                    founded_date=extract_year(row.get("Date Joined")),
                    country_code=self.clean_string(row.get("Country")),
                    city=self.clean_string(row.get("City")),
                    industries=self.parse_industries(row.get("Industry")),
                    is_ai_related="artificial intelligence" in row.get("Industry", "").lower(),
                    raw={**row, "_extraction_source": "startups_2021"}
                )
                
                if self._safe_add_entity(entity):
                    self.session.flush() 
                    count += 1

                    # 3. GESTION DES INVESTISSEURS (Stockage propre dans Entity + lien dans raw)
                    investors_raw = row.get("Select Investors", "")
                    if investors_raw:
                        investors_list = [i.strip() for i in investors_raw.split(",") if i.strip()]
                        investor_refs = []

                        for inv_name in investors_list:
                            # On cherche ou crée l'entité Investisseur dans la table Entity
                            investor_ent = self.session.exec(
                                select(Entity).where(Entity.name == inv_name)
                            ).first()

                            if not investor_ent:
                                investor_ent = Entity(
                                    source_id=self.source_id,
                                    name=inv_name,
                                    type="investor",
                                    is_ai_related=entity.is_ai_related,
                                    raw={"_first_seen_investing_in": name}
                                )
                                self.session.add(investor_ent)
                                self.session.flush()
                            
                            # On stocke une référence légère dans le raw de l'entreprise
                            investor_refs.append({
                                "id": investor_ent.id,
                                "name": investor_ent.name
                            })

                        # Mise à jour du champ raw avec les liens vers les investisseurs
                        entity.raw["investor_links"] = investor_refs
                        self.session.add(entity)
            
            self.session.commit()
            return count

    def process_crunchbase_csv(self) -> int:
        """Source 1: Crunchbase (Version stable avec mapping Author & Entity correct)."""
        import re
        import csv
        path = self.data_dir / "Crunchbase_csv.csv"
        if not path.exists(): return 0
        count = 0
        
        def extract_year(s) -> Optional[str]:
            if not s: return None
            # Cherche 4 chiffres commençant par 19 ou 20
            match = re.search(r'\b(18|19|20)\d{2}\b', str(s))
            return match.group(0) if match else None

        def clean_money(s) -> Optional[float]:
            if not s or s in ("—", ""): return None
            # Nettoie les virgules et espaces pour le parsing numérique
            s = str(s).strip().replace(",", "").replace(" ", "").replace("$", "")
            try:
                return float(s)
            except:
                return self.parse_number(s)

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=',', quotechar='"')

            for row in reader:
                # 1. IDENTITÉ
                name = self.clean_string(row.get("Organization Name"))
                if not name: continue

                # 2. GÉOGRAPHIE
                loc_raw = row.get("Headquarters Location")
                city, country_code = None, None
                if loc_raw:
                    parts = [p.strip() for p in loc_raw.split(",")]
                    city = parts[0]
                    country_name = parts[-1]
                    mapping = {"United States": "USA", "France": "FRA", "China": "CHN", "Germany": "DEU", "Singapore": "SGP", "UK": "GBR"}
                    country_code = mapping.get(country_name, country_name[:3].upper())

                # 3. FINANCE
                total_funding = clean_money(row.get("Total Funding Amount"))
                rev_raw = row.get("Estimated Revenue Range", "")
                valuation = clean_money(row.get("Last Funding Amount")) # On prend le dernier montant si valuation absente

                # 4. DATES (Fix Founded Year)
                founded_year = extract_year(row.get("Founded Date"))
                last_funding_year = extract_year(row.get("Last Funding Date"))

                # 5. INDUSTRIES
                industries_list = self.parse_industries(row.get("Industries", ""))

                entity = Entity(
                    source_id=self.source_id,
                    name=name,
                    type="company",
                    website=row.get("Website"),
                    city=city,
                    country_code=country_code,
                    operating_status=row.get("Operating Status", "Active"),
                    total_funding=total_funding,
                    valuation=valuation,
                    estimated_revenue=rev_raw,
                    founded_date=founded_year,
                    last_funding_date=last_funding_year,
                    industries=industries_list,
                    is_ai_related=True,
                    raw={"row": row, "_extraction_source": "crunchbase_v9_stable"}
                )
                
                if self._safe_add_entity(entity): 
                    self.session.flush()
                    count += 1

                # --- GESTION DES INVESTISSEURS (SÉCURISÉE) ---
                    investors_raw = row.get("Lead Investors")
                    if investors_raw and investors_raw != "—":
                        # On sépare par point-virgule
                        investors_list = [i.strip() for i in investors_raw.split(";") if i.strip()]
                        inv_links = []
                        for inv_name in investors_list:
                            # SÉCURITÉ : On ignore les investisseurs qui ressemblent à des nombres (brevets décalés)
                            if any(char.isdigit() for char in inv_name) or len(inv_name) < 3:
                                continue

                            inv_ent = self.session.exec(select(Entity).where(Entity.name == inv_name)).first()
                            if not inv_ent:
                                inv_ent = Entity(
                                    source_id=self.source_id, 
                                    name=inv_name, 
                                    type="investor", 
                                    is_ai_related=True
                                )
                                self.session.add(inv_ent)
                                self.session.flush()
                            inv_links.append({"id": inv_ent.id, "name": inv_ent.name})
                        entity.raw["investor_links"] = inv_links

                    # --- GESTION DES FONDATEURS ---
                    founders_raw = row.get("Founders")
                    if founders_raw:
                        f_list = [f.strip() for f in founders_raw.split(";") if f.strip()]
                        for f_name in f_list:
                            # --- FILTRE ANTI-DÉCALAGE ---
                            # On ignore les noms qui contiennent des chiffres (ex: 251-500)
                            # ou qui sont purement numériques.
                            if any(char.isdigit() for char in f_name) or len(f_name) < 3:
                                continue
                            
                            p_slug = f"person_{f_name.lower().replace(' ', '_')}"
                            
                            person = self.session.exec(
                                select(Author).where(Author.external_id == p_slug)
                            ).first()
                            
                            if not person:
                                person = Author(
                                    full_name=f_name, 
                                    external_id=p_slug,
                                    publication_count=0
                                )
                                self.session.add(person)
                                self.session.flush()
                            
                            # CORRECTION ICI : Ajout de author_external_id=p_slug
                            self.session.add(Affiliation(
                                author_id=person.id, 
                                author_external_id=p_slug, # <--- INDISPENSABLE
                                entity_id=entity.id, 
                                role="Founder",
                                source_name="crunchbase_ingestion"
                            ))

        self.session.commit()
        return count
