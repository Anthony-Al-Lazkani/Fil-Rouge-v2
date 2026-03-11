"""
Processeur d'ingestion des organisations (Universités, Labos, Startups).

Features:
- Unification de 5 sources locales : Crunchbase, Startup-Dataset, Global Success, 2021-end, et AI_Companies.
- Nettoyage et normalisation des métriques financières (conversions K/M/B).
- Extraction géographique et déduplication par nom.
- Insertion directe via SQLModel sans passer par des schémas intermédiaires.
"""

import csv
from pathlib import Path
from typing import List, Optional
from sqlmodel import Session, select 
from database import engine
from models import Entity, Source

class OrganizationProcessor:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.session = Session(engine)
        # Initialisation de la source locale
        source = self.session.exec(select(Source).where(Source.name == "local_startup_db")).first()
        if not source:
            source = Source(name="local_startup_db", type="business")
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        self.source_id = source.id

    # --- MÉTHODES DE NETTOYAGE (Statiques) ---

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

    # --- MÉTHODES D'INGESTION (Directes en BDD) ---

    def _safe_add_entity(self, entity: Entity):
        """Vérifie le doublon par nom avant d'ajouter."""
        existing = self.session.exec(select(Entity).where(Entity.name == entity.name)).first()
        if not existing:
            self.session.add(entity)
            return True
        return False

    def process_crunchbase_csv(self) -> int:
        """Source 1: Crunchbase_csv (La plus riche)."""
        path = self.data_dir / "Crunchbase_csv.csv"
        if not path.exists(): return 0
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = self.clean_string(row.get("Organization Name"))
                if not name: continue
                
                loc_raw = row.get("Headquarters Location", "")
                city = loc_raw.split(",")[0].strip() if loc_raw else None

                entity = Entity(
                    source_id=self.source_id,
                    name=name,
                    type="company",
                    website=row.get("Website"),
                    description=row.get("Description"),
                    founded_date=self.clean_string(row.get("Founded Date")),
                    operating_status=self.clean_string(row.get("Operating Status")),
                    total_funding=self.parse_number(row.get("Total Funding Amount")),
                    valuation=self.parse_number(row.get("Estimated Revenue Range")),
                    industries=self.parse_industries(row.get("Industries")),
                    is_ai_related=True,
                    city=city,
                    founders=[f.strip() for f in row.get("Founders", "").split(";") if f],
                    raw=row
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
                
                ai_focus = self.clean_string(row.get("Percent AI Service Focus"))
                ai_focus = int(ai_focus.replace("%", "")) if ai_focus else None

                entity = Entity(
                    source_id=self.source_id,
                    name=name,
                    type="company",
                    website=self.clean_string(row.get("Website")),
                    ai_focus_percent=ai_focus,
                    is_ai_related=True,
                    raw=row
                )
                if self._safe_add_entity(entity): count += 1
        self.session.commit()
        return count

    def process_startup_dataset(self) -> int:
        """Source 3: Startup-Dataset.csv."""
        path = self.data_dir / "Startup-Dataset.csv"
        if not path.exists(): return 0
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = self.clean_string(row.get("Name"))
                if not name: continue
                
                entity = Entity(
                    source_id=self.source_id,
                    name=name,
                    type="company",
                    country=self.clean_string(row.get("Country")),
                    description=self.clean_string(row.get("Description")),
                    founded_date=self.clean_string(row.get("Launch Date")),
                    raw=row
                )
                if self._safe_add_entity(entity): count += 1
        self.session.commit()
        return count

    def process_global_startup_success(self) -> int:
        """Source 4: global_startup_success_dataset.csv."""
        path = self.data_dir / "global_startup_success_dataset.csv"
        if not path.exists(): return 0
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = self.clean_string(row.get("Startup Name"))
                if not name: continue
                
                entity = Entity(
                    source_id=self.source_id,
                    name=name,
                    type="company",
                    total_funding=self.parse_number(row.get("Total Funding ($M)")),
                    valuation=self.parse_number(row.get("Valuation ($B)")),
                    is_ai_related="ai" in row.get("Industry", "").lower(),
                    raw=row
                )
                if self._safe_add_entity(entity): count += 1
        self.session.commit()
        return count

    def process_startups_2021(self) -> int:
        """Source 5: Startups-in-2021-end.csv."""
        path = self.data_dir / "Startups-in-2021-end.csv"
        if not path.exists(): return 0
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            try:
                next(reader); next(reader) # Skip headers
                for row in reader:
                    if len(row) < 2: continue
                    name = self.clean_string(row[1])
                    if not name: continue
                    entity = Entity(
                        source_id=self.source_id,
                        name=name,
                        type="company",
                        valuation=self.parse_number(row[2]) if len(row) > 2 else None,
                        raw={"row": row}
                    )
                    if self._safe_add_entity(entity): count += 1
            except StopIteration: pass
        self.session.commit()
        return count