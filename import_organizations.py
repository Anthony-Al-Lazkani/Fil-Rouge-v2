import csv
import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = Path(__file__).parent / "database.db"


def clean_string(s):
    """Clean string for display."""
    if s is None:
        return None
    s = str(s).strip()
    if s.lower() in ("n/a", "nan", "", "none", "undisclosed"):
        return None
    return s


def parse_number(s):
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


def extract_location(location_str):
    """Extract city and country from location string."""
    if not location_str:
        return None, None
    parts = location_str.split(",")
    if len(parts) >= 2:
        city = parts[0].strip()
        country = parts[-1].strip()
        return city, country
    return location_str.strip(), None


def parse_industries(industries_str):
    """Parse industries into list."""
    if not industries_str:
        return []
    return [i.strip() for i in industries_str.split(",")]


def is_likely_name(s):
    """Check if string looks like a person's name (not a number/employee count)."""
    if not s:
        return False
    s = s.strip()
    # Filter out pure numbers, ranges like "1001-5000", etc.
    if re.match(r"^\d+[-\d]*$", s):
        return False
    if s.lower() in ("n/a", "nan", "undisclosed"):
        return False
    return True


def import_crunchbase():
    """Import Crunchbase CSV data."""
    print("Importing Crunchbase data...")
    path = DATA_DIR / "Crunchbase_csv"
    if not path.exists():
        print("Crunchbase file not found")
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    count = 0

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = clean_string(row.get("Organization Name"))
            if not name:
                continue

            location = clean_string(row.get("Headquarters Location"))
            city, country = extract_location(location)

            industries = parse_industries(clean_string(row.get("Industries")))
            is_ai = any(
                "ai" in i.lower() or "artificial intelligence" in i.lower()
                for i in industries
            )

            founders_str = clean_string(row.get("Founders"))
            founders = []
            if founders_str:
                for f in founders_str.split(";"):
                    f = f.strip()
                    if is_likely_name(f):
                        founders.append(f)

            cur.execute(
                """
                INSERT OR IGNORE INTO organization (
                    source, name, type, country, city, description,
                    founded_date, industries, operating_status, number_of_employees,
                    estimated_revenue, website, total_funding, last_funding_amount,
                    last_funding_date, number_of_funding_rounds, number_of_investors,
                    valuation, acquisition_count, ipo, acquired, founders,
                    number_of_founders, is_ai_related, ai_focus_percent, raw
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "crunchbase",
                    name,
                    "company",
                    country,
                    city,
                    clean_string(row.get("Description")),
                    clean_string(row.get("Founded Date")),
                    json.dumps(industries),
                    clean_string(row.get("Operating Status")),
                    clean_string(row.get("Number of Employees")),
                    clean_string(row.get("Estimated Revenue Range")),
                    clean_string(row.get("Website")),
                    parse_number(row.get("Total Funding Amount")),
                    parse_number(row.get("Last Funding Amount")),
                    clean_string(row.get("Last Funding Date")),
                    clean_string(row.get("Number of Funding Rounds")),
                    clean_string(row.get("Number of Investors")),
                    parse_number(row.get("Valuation")),
                    clean_string(row.get("Number of Acquisitions")),
                    True if clean_string(row.get("IPO?")) == "Yes" else None,
                    True if clean_string(row.get("Acquired?")) == "Yes" else None,
                    json.dumps(founders),
                    len(founders) if founders else None,
                    is_ai,
                    None,
                    json.dumps(dict(row)),
                ),
            )
            count += 1

    conn.commit()
    conn.close()
    print(f"Imported {count} organizations from Crunchbase")
    return count


def import_startup_dataset():
    """Import Startup-Dataset CSV data."""
    print("Importing Startup-Dataset data...")
    path = DATA_DIR / "Startup-Dataset.csv"
    if not path.exists():
        print("Startup-Dataset file not found")
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    count = 0

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = clean_string(row.get("Name"))
            if not name:
                continue

            location = clean_string(row.get("Country"))
            country = location
            city = None

            founders_str = clean_string(row.get("Founders"))
            founders = (
                [f.strip() for f in founders_str.split(",")] if founders_str else []
            )

            description = clean_string(row.get("Description"))

            cur.execute(
                """
                INSERT OR IGNORE INTO organization (
                    source, name, type, country, city, description,
                    founded_date, operating_status, founders,
                    number_of_founders, raw
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "startup-dataset",
                    name,
                    "company",
                    country,
                    city,
                    description,
                    clean_string(row.get("Launch Date")),
                    clean_string(row.get("Current Status")),
                    json.dumps(founders),
                    len(founders) if founders else None,
                    json.dumps(dict(row)),
                ),
            )
            count += 1

    conn.commit()
    conn.close()
    print(f"Imported {count} organizations from Startup-Dataset")
    return count


def import_global_startup_success():
    """Import global_startup_success_dataset CSV data."""
    print("Importing global_startup_success_dataset data...")
    path = DATA_DIR / "global_startup_success_dataset.csv"
    if not path.exists():
        print("global_startup_success_dataset file not found")
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    count = 0

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = clean_string(row.get("Startup Name"))
            if not name:
                continue

            industries = parse_industries(clean_string(row.get("Industry")))
            is_ai = any(
                "ai" in i.lower() or "artificial intelligence" in i.lower()
                for i in industries
            )

            cur.execute(
                """
                INSERT OR IGNORE INTO organization (
                    source, name, type, country, founded_date,
                    industries, operating_status, total_funding,
                    number_of_employees, valuation, ipo, acquired,
                    is_ai_related, raw
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "global_startup_success",
                    name,
                    "company",
                    clean_string(row.get("Country")),
                    clean_string(row.get("Founded Year")),
                    json.dumps(industries),
                    "Active"
                    if clean_string(row.get("Acquired?")) != "Yes"
                    else "Acquired",
                    parse_number(row.get("Total Funding ($M)")),
                    clean_string(row.get("Number of Employees")),
                    parse_number(row.get("Valuation ($B)")),
                    True if clean_string(row.get("IPO?")) == "Yes" else None,
                    True if clean_string(row.get("Acquired?")) == "Yes" else None,
                    is_ai,
                    json.dumps(dict(row)),
                ),
            )
            count += 1

    conn.commit()
    conn.close()
    print(f"Imported {count} organizations from global_startup_success_dataset")
    return count


def import_startups_2021():
    """Import Startups-in-2021-end CSV data."""
    print("Importing Startups-in-2021-end data...")
    path = DATA_DIR / "Startups-in-2021-end.csv"
    if not path.exists():
        print("Startups-in-2021-end file not found")
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    count = 0

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip empty first column header
        next(reader)  # skip header row

        for row in reader:
            if len(row) < 2:
                continue
            name = clean_string(row[1])  # Company column
            if not name:
                continue

            city = clean_string(row[5]) if len(row) > 5 else None
            country = clean_string(row[4]) if len(row) > 4 else None

            industries = parse_industries(clean_string(row[6])) if len(row) > 6 else []
            is_ai = any(
                "ai" in i.lower() or "artificial intelligence" in i.lower()
                for i in industries
            )

            valuation = parse_number(row[2]) if len(row) > 2 else None

            cur.execute(
                """
                INSERT OR IGNORE INTO organization (
                    source, name, type, country, city,
                    industries, valuation, is_ai_related, raw
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "startups_2021",
                    name,
                    "company",
                    country,
                    city,
                    json.dumps(industries),
                    valuation,
                    is_ai,
                    json.dumps({"row": row}),
                ),
            )
            count += 1

    conn.commit()
    conn.close()
    print(f"Imported {count} organizations from Startups-in-2021-end")
    return count


def import_ai_companies():
    """Import AI_Companies CSV data."""
    print("Importing AI_Companies data...")
    path = DATA_DIR / "AI_Companies.csv"
    if not path.exists():
        print("AI_Companies file not found")
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    count = 0

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = clean_string(row.get("Company_Name"))
            if not name:
                continue

            location = clean_string(row.get("Location"))
            city, country = extract_location(location)

            ai_focus = clean_string(row.get("Percent AI Service Focus"))
            if ai_focus:
                ai_focus = ai_focus.replace("%", "")
                try:
                    ai_focus = int(ai_focus)
                except:
                    ai_focus = None

            cur.execute(
                """
                INSERT OR IGNORE INTO organization (
                    source, name, type, country, city,
                    website, number_of_employees, ai_focus_percent,
                    is_ai_related, raw
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "ai_companies",
                    name,
                    "company",
                    country,
                    city,
                    clean_string(row.get("Website")),
                    clean_string(row.get("Number of Employees")),
                    ai_focus,
                    True,
                    json.dumps(dict(row)),
                ),
            )
            count += 1

    conn.commit()
    conn.close()
    print(f"Imported {count} organizations from AI_Companies")
    return count


def get_org_count():
    """Get total organization count."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM organization")
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_all_founders():
    """Get all unique founders from database."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, founders FROM organization WHERE founders IS NOT NULL"
    )
    rows = cur.fetchall()
    conn.close()

    all_founders = set()
    for org_id, org_name, founders_json in rows:
        if founders_json:
            try:
                founders = json.loads(founders_json)
                for f in founders:
                    all_founders.add((org_id, org_name, f))
            except:
                pass
    return all_founders


if __name__ == "__main__":
    print("=" * 50)
    print("Starting import...")
    print("=" * 50)

    import_crunchbase()
    import_startup_dataset()
    import_global_startup_success()
    import_startups_2021()
    import_ai_companies()

    print("=" * 50)
    print(f"Total organizations in database: {get_org_count()}")
    print("=" * 50)

    # Show sample founders
    founders = get_all_founders()
    print(f"\nTotal unique founders found: {len(founders)}")
    print("\nSample founders:")
    for org_id, org_name, founder in list(founders)[:10]:
        print(f"  - {founder} ({org_name})")
