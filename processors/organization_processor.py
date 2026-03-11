"""
Processeur d'ingestion des organisations (Universités, Labos, Startups).

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
from models import Entity, Source

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

    def process_crunchbase_csv(self) -> int:
        """Source 1: Crunchbase (Récupération totale via scan de contenu)."""
        path = self.data_dir / "Crunchbase_csv.csv"
        if not path.exists(): return 0
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None) # Skip header

            for row in reader:
                if not row or len(row) < 5: continue
                
                name = self.clean_string(row[0])
                if not name: continue

                # --- 1. IDENTIFICATION DES PIVOTS (Website & Localisation) ---
                web_idx = next((i for i, c in enumerate(row) if "." in str(c) and any(ext in str(c).lower() for ext in [".com", ".ai", ".io"])), -1)
                loc_raw = next((c for c in row if any(country in str(c) for country in ["United States", "France", "China", "UK", "Germany", "Japan"])), None)

                # --- 2. EXTRACTION FINANCIÈRE ---
                money_cells = [c for c in row if "$" in str(c)]
                amounts = []
                for mc in money_cells:
                    val = self.parse_number(mc.split("to")[-1])
                    if val: amounts.append(val)
                
                total_funding = max(amounts) if amounts else None
                valuation = min(amounts) if len(amounts) > 1 else None

                # --- 3. DATES & STATUS ---
                last_funding_date = next((c for c in row if any(y in str(c) for y in ["2024", "2025", "2026"])), None)
                founded_date = next((c for c in row if any(m in str(c) for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]) and c != last_funding_date), None)

                # --- 4. INDUSTRIES ---
                industries_raw = next((c for c in row if "," in str(c) and len(str(c)) > 10 and c != loc_raw and len(str(c)) < 100), None)

                entity = Entity(
                    source_id=self.source_id,
                    name=name,
                    type="company",
                    website=row[web_idx] if web_idx != -1 else None,
                    city=loc_raw.split(",")[0].strip() if loc_raw else None,
                    country_code="USA" if loc_raw and "United States" in loc_raw else None,
                    operating_status="Successful",
                    total_funding=total_funding,
                    valuation=valuation,
                    founded_date=founded_date,
                    last_funding_date=last_funding_date,
                    industries=self.parse_industries(industries_raw) if industries_raw else [],
                    is_ai_related=True,
                    raw={"row": row, "_extraction_source": "crunchbase_v4_deep_scan"}
                )
                if self._safe_add_entity(entity): count += 1

        self.session.commit()
        return count

    def process_ai_companies(self) -> int:
        """Source 2: AI_Companies (Focus IA)."""
        path = self.data_dir / "AI_Companies.csv"
        if not path.exists(): return 0
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = self.clean_string(row.get("Company_Name"))
                if not name: continue
                
                loc_raw = row.get("Location", "")
                city = loc_raw.split(",")[0].strip() if loc_raw and "," in loc_raw else None
                country_code = "USA" 
                
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
                    is_ai_related=True,
                    raw={**row, "_extraction_source": "ai_companies"}
                )
                if self._safe_add_entity(entity): count += 1
        self.session.commit()
        return count

    def process_startup_dataset(self) -> int:
        """Source 3: Startup-Dataset.csv (Focus Croissance & Revenus)."""
        path = self.data_dir / "Startup-Dataset.csv"
        if not path.exists(): return 0
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = self.clean_string(row.get("Name"))
                if not name: continue
                
                founders_raw = row.get("Founders", "")
                founders_list = [f.strip() for f in founders_raw.split(",") if f]
                rev_y3 = self.parse_number(row.get("Revenue Year 3"))

                entity = Entity(
                    source_id=self.source_id,
                    name=name,
                    type="company",
                    country_code=self.clean_string(row.get("Country")),
                    description=self.clean_string(row.get("Description")),
                    founded_date=self.clean_string(row.get("Launch Date")),
                    operating_status=self.clean_string(row.get("Current Status")),
                    total_funding=rev_y3, 
                    founders=founders_list,
                    is_ai_related=False, 
                    raw={**row, "_extraction_source": "startup_dataset_growth"}
                )
                if self._safe_add_entity(entity): count += 1
        self.session.commit()
        return count

    def process_startups_2021(self) -> int:
        """Source 4: Startups-in-2021-end.csv (Nettoyage final)."""
        path = self.data_dir / "Startups-in-2021-end.csv"
        if not path.exists(): return 0
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = self.clean_string(row.get("Company"))
                if not name: continue
                
                val_raw = row.get("Valuation ($B)", "0").replace("$", "")
                try:
                    valuation = float(val_raw) * 1_000_000_000
                except:
                    valuation = None

                entity = Entity(
                    source_id=self.source_id,
                    name=name,
                    type="company",
                    valuation=valuation,
                    founded_date=self.clean_string(row.get("Date Joined")),
                    country_code=self.clean_string(row.get("Country")),
                    city=self.clean_string(row.get("City")),
                    industries=self.parse_industries(row.get("Industry")),
                    is_ai_related="artificial intelligence" in row.get("Industry", "").lower(),
                    raw={**row, "_extraction_source": "startups_2021"}
                )
                
                if self._safe_add_entity(entity): count += 1
        
        self.session.commit()
        return count