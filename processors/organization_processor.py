import csv
import re
from pathlib import Path
from typing import Optional, List

from schemas.organization import OrganizationCreate


class OrganizationProcessor:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    @staticmethod
    def clean_string(s) -> Optional[str]:
        """Clean string for display."""
        if s is None:
            return None
        s = str(s).strip()
        if s.lower() in ("n/a", "nan", "", "none", "undisclosed"):
            return None
        return s

    @staticmethod
    def parse_number(s) -> Optional[float]:
        """Parse number from string like '$1B' or '1000'."""
        if s is None:
            return None
        s = str(s).strip()
        if not s or s.lower() in ("n/a", "undisclosed"):
            return None
        s = s.replace(",", "").replace("$", "").replace(" ", "")
        multipliers = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}
        for suffix, mult in multipliers.items():
            if suffix in s.lower():
                try:
                    return float(s.lower().replace(suffix, "")) * mult
                except:
                    return None
        try:
            return float(s)
        except:
            return None

    @staticmethod
    def extract_location(location_str: str) -> tuple[Optional[str], Optional[str]]:
        """Extract city and country from location string."""
        if not location_str:
            return None, None
        parts = location_str.split(",")
        if len(parts) >= 2:
            city = parts[0].strip()
            country = parts[-1].strip()
            return city, country
        return location_str.strip(), None

    @staticmethod
    def parse_industries(industries_str: str) -> List[str]:
        """Parse industries into list."""
        if not industries_str:
            return []
        return [i.strip() for i in industries_str.split(",")]

    def process_startup_dataset(self) -> List[OrganizationCreate]:
        """Process Startup-Dataset CSV file."""
        path = self.data_dir / "Startup-Dataset.csv"
        if not path.exists():
            return []

        organizations = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = self.clean_string(row.get("Name"))
                if not name:
                    continue

                location = self.clean_string(row.get("Country"))
                country = location

                founders_str = self.clean_string(row.get("Founders"))
                founders = (
                    [f.strip() for f in founders_str.split(",")] if founders_str else []
                )

                org = OrganizationCreate(
                    source="startup-dataset",
                    name=name,
                    type="company",
                    country=country,
                    description=self.clean_string(row.get("Description")),
                    founded_date=self.clean_string(row.get("Launch Date")),
                    operating_status=self.clean_string(row.get("Current Status")),
                    founders=founders,
                    number_of_founders=len(founders) if founders else None,
                )
                organizations.append(org)

        return organizations

    def process_global_startup_success(self) -> List[OrganizationCreate]:
        """Process global_startup_success_dataset CSV file."""
        path = self.data_dir / "global_startup_success_dataset.csv"
        if not path.exists():
            return []

        organizations = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = self.clean_string(row.get("Startup Name"))
                if not name:
                    continue

                industries = self.parse_industries(
                    self.clean_string(row.get("Industry"))
                )
                is_ai = any(
                    "ai" in i.lower() or "artificial intelligence" in i.lower()
                    for i in industries
                )

                org = OrganizationCreate(
                    source="global_startup_success",
                    name=name,
                    type="company",
                    country=self.clean_string(row.get("Country")),
                    founded_date=self.clean_string(row.get("Founded Year")),
                    industries=industries,
                    operating_status="Acquired"
                    if self.clean_string(row.get("Acquired?")) == "Yes"
                    else "Active",
                    total_funding=self.parse_number(row.get("Total Funding ($M)")),
                    number_of_employees=self.clean_string(
                        row.get("Number of Employees")
                    ),
                    valuation=self.parse_number(row.get("Valuation ($B)")),
                    ipo=self.clean_string(row.get("IPO?")) == "Yes",
                    acquired=self.clean_string(row.get("Acquired?")) == "Yes",
                    is_ai_related=is_ai,
                )
                organizations.append(org)

        return organizations

    def process_startups_2021(self) -> List[OrganizationCreate]:
        """Process Startups-in-2021-end CSV file."""
        path = self.data_dir / "Startups-in-2021-end.csv"
        if not path.exists():
            return []

        organizations = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip empty first column header
            next(reader)  # skip header row

            for row in reader:
                if len(row) < 2:
                    continue
                name = self.clean_string(row[1])
                if not name:
                    continue

                city = self.clean_string(row[5]) if len(row) > 5 else None
                country = self.clean_string(row[4]) if len(row) > 4 else None

                industries = self.parse_industries(
                    self.clean_string(row[6]) if len(row) > 6 else None
                )
                is_ai = any(
                    "ai" in i.lower() or "artificial intelligence" in i.lower()
                    for i in industries
                )

                valuation = self.parse_number(row[2]) if len(row) > 2 else None

                org = OrganizationCreate(
                    source="startups_2021",
                    name=name,
                    type="company",
                    country=country,
                    city=city,
                    industries=industries,
                    valuation=valuation,
                    is_ai_related=is_ai,
                )
                organizations.append(org)

        return organizations

    def process_ai_companies(self) -> List[OrganizationCreate]:
        """Process AI_Companies CSV file."""
        path = self.data_dir / "AI_Companies.csv"
        if not path.exists():
            return []

        organizations = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = self.clean_string(row.get("Company_Name"))
                if not name:
                    continue

                location = self.clean_string(row.get("Location"))
                city, country = self.extract_location(location)

                ai_focus = self.clean_string(row.get("Percent AI Service Focus"))
                if ai_focus:
                    ai_focus = ai_focus.replace("%", "")
                    try:
                        ai_focus = int(ai_focus)
                    except:
                        ai_focus = None

                org = OrganizationCreate(
                    source="ai_companies",
                    name=name,
                    type="company",
                    country=country,
                    city=city,
                    website=self.clean_string(row.get("Website")),
                    number_of_employees=self.clean_string(
                        row.get("Number of Employees")
                    ),
                    ai_focus_percent=ai_focus,
                    is_ai_related=True,
                )
                organizations.append(org)

        return organizations
