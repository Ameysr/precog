"""Sector data utilities — no circular dependencies."""

import json
from pathlib import Path

SECTORS_PATH = Path("data/sectors/sectors.json")
SECTORS_DIR = Path("data/sectors")


def load_sectors() -> dict:
    if not SECTORS_PATH.exists():
        return {"sectors": {}}
    with open(SECTORS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_sector_for_business_type(business_type: str) -> str | None:
    sectors = load_sectors()
    bt_lower = business_type.lower()
    for sector_name, sector in sectors["sectors"].items():
        for bt in sector["business_types"]:
            if bt in bt_lower or bt_lower in bt:
                return sector_name
    return None


def load_sector_bank(sector_name: str) -> dict | None:
    path = SECTORS_DIR / sector_name / "language_bank.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def sector_bank_exists(sector_name: str) -> bool:
    return (SECTORS_DIR / sector_name / "language_bank.json").exists()
