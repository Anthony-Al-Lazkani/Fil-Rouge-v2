from sqlmodel import Session, select, SQLModel
from database.initialize import engine
from models.source import Source
from models.research_item import ResearchItem
from models.author import Author
from models.affiliation import Affiliation
from models.entity import Entity
from models.organization import Organization  # Deprecated
from models.institution import Institution  # Deprecated


TABLES = {
    "affiliation": Affiliation,
    "author": Author,
    "entity": Entity,
    "institution": Institution,  # Deprecated: use entity instead
    "organization": Organization,  # Deprecated: use entity instead
    "research_item": ResearchItem,
    "source": Source,
}


class TableService:
    def delete_table(self, table_name: str) -> bool:
        """Delete all records from a specific table"""
        table_name = table_name.lower()
        if table_name not in TABLES:
            raise ValueError(
                f"Unknown table: {table_name}. Available: {list(TABLES.keys())}"
            )

        model = TABLES[table_name]
        with Session(engine) as session:
            session.exec(model.__table__.delete())
            session.commit()
        return True

    def delete_tables(self, table_names: list[str]) -> dict:
        """Delete multiple tables"""
        results = {}
        for name in table_names:
            try:
                results[name] = self.delete_table(name)
            except Exception as e:
                results[name] = str(e)
        return results

    def list_tables(self) -> list:
        """List all available tables"""
        return list(TABLES.keys())


if __name__ == "__main__":
    import sys

    service = TableService()

    if len(sys.argv) < 2:
        print("Available tables:", service.list_tables())
        print(
            "\nUsage: python -m database.table_service <table_name> [table_name2 ...]"
        )
        print("Example: python -m database.table_service institution")
        sys.exit(1)

    tables_to_delete = [t.lower() for t in sys.argv[1:]]
    results = service.delete_tables(tables_to_delete)

    for table, result in results.items():
        if result is True:
            print(f"✓ Deleted table: {table}")
        else:
            print(f"✗ Failed to delete {table}: {result}")
