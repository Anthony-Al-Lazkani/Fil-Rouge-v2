import json
from pathlib import Path
from typing import List, Dict, Any


def crawl_hal_ai() -> List[Dict[str, Any]]:
    """
    Load HAL data from existing JSONL file.
    Returns a list of processed records ready for database insertion.
    """
    data_file = Path(__file__).parent.parent / "data" / "hal_publications.jsonl"

    if not data_file.exists():
        print(f"HAL data file not found: {data_file}")
        return []

    records = []
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        records.append(record)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing line {line_num}: {e}")
                        continue

        print(f"Loaded {len(records)} HAL records from {data_file}")

    except Exception as e:
        print(f"Error loading HAL data file: {e}")

    return records
