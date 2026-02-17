#!/usr/bin/env python3
"""
CLI for importing startup/company data from CSV files into the database.

Usage:
    python scripts/import_startups.py              # Import all startup data
    python scripts/import_startups.py --source ai_companies  # Import specific source
"""

import argparse
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.initialize import create_db_and_tables
from processors.organization_processor import OrganizationProcessor
from services.organization_service import OrganizationService
from sqlmodel import Session, create_engine
from database.initialize import engine


def import_all():
    """Import all CSV startup data."""
    processor = OrganizationProcessor(project_root / "data")
    service = OrganizationService()

    all_orgs = []

    # Process each CSV source
    for method in [
        processor.process_startup_dataset,
        processor.process_global_startup_success,
        processor.process_startups_2021,
        processor.process_ai_companies,
    ]:
        orgs = method()
        all_orgs.extend(orgs)

    with Session(engine) as session:
        count = service.create_many(session, all_orgs)

        # Show founders
        companies = service.get_companies_with_founders(session)
        founders_set = set()
        for org in companies:
            if org.founders:
                for f in org.founders:
                    founders_set.add((f, org.name))

        print(f"Created/updated {count} organizations")
        print(f"Found {len(companies)} companies with founders")
        print(f"Total unique founders: {len(founders_set)}")

        if founders_set:
            print("\nSample founders:")
            for founder, company in list(founders_set)[:10]:
                print(f"  - {founder} ({company})")


def import_single(source: str):
    """Import a single CSV source."""
    processor = OrganizationProcessor(project_root / "data")
    service = OrganizationService()

    method_map = {
        "startup-dataset": processor.process_startup_dataset,
        "global_startup_success": processor.process_global_startup_success,
        "startups_2021": processor.process_startups_2021,
        "ai_companies": processor.process_ai_companies,
    }

    print(f"\nProcessing {source}...")
    orgs = method_map[source]()

    with Session(engine) as session:
        count = service.create_many(session, orgs)
        print(f"Created/updated {count} organizations")


def main():
    parser = argparse.ArgumentParser(
        description="Import startup/company data from CSV files into the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--source",
        choices=[
            "startup-dataset",
            "global_startup_success",
            "startups_2021",
            "ai_companies",
            "all",
        ],
        default="all",
        help="Which source to import (default: all)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("STARTUP/COMPANY DATA IMPORT")
    print("=" * 60)

    print("\nInitializing database...")
    create_db_and_tables()

    if args.source == "all":
        import_all()
    else:
        import_single(args.source)

    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
