"""Pre-build sector language banks by scraping companies WITH Google Play apps.
Run once to cache data. Subsequent runs use the cache."""

import json
import time
from pathlib import Path

from scraper_reviews import scrape_google_play, build_language_bank, LanguageBank
from utils import save_json
from sectors import load_sectors, SECTORS_DIR


def sector_bank_path(sector_name: str) -> Path:
    return SECTORS_DIR / sector_name / "language_bank.json"


def sector_reviews_path(sector_name: str) -> Path:
    return SECTORS_DIR / sector_name / "raw_reviews.json"


def sector_exists(sector_name: str) -> bool:
    return sector_bank_path(sector_name).exists()


def build_sector_bank(sector_name: str, force: bool = False) -> LanguageBank | None:
    sectors = load_sectors()
    sector = sectors["sectors"].get(sector_name)
    if not sector:
        print(f"Sector '{sector_name}' not found")
        return None

    if sector_exists(sector_name) and not force:
        print(f"  [i] Sector '{sector_name}' already built. Use force=True to rebuild.")
        with open(sector_bank_path(sector_name), "r", encoding="utf-8") as f:
            data = json.load(f)
        return LanguageBank(**data)

    (SECTORS_DIR / sector_name).mkdir(exist_ok=True)
    all_reviews = []
    source_companies = sector["source_companies"]

    for comp in source_companies:
        print(f"\n  Scraping {comp['name']} ({comp['app_id']})...")
        reviews = scrape_google_play(comp["app_id"], count=200)
        for r in reviews:
            r["source_company"] = comp["name"]
        all_reviews.extend(reviews)
        print(f"    Got {len(reviews)} reviews (total: {len(all_reviews)})")
        time.sleep(1)

    if not all_reviews:
        print(f"  [!] No reviews found for sector '{sector_name}'")
        return None

    sector_dir = SECTORS_DIR / sector_name
    sector_dir.mkdir(parents=True, exist_ok=True)

    # Save raw reviews
    save_json(
        {"sector": sector_name, "source_companies": source_companies, "total": len(all_reviews), "reviews": all_reviews},
        filename=str(sector_reviews_path(sector_name).name),
        directory=sector_dir,
    )

    # Build language bank from all reviews combined
    combined_name = f"{sector_name} sector ({', '.join(c['name'] for c in source_companies)})"
    print(f"\n  Building language bank from {len(all_reviews)} reviews...")
    bank = build_language_bank(combined_name, all_reviews)

    bank_payload = {
        "sector": sector_name,
        "source_companies": [c["name"] for c in source_companies],
        "total_reviews": len(all_reviews),
        **bank.model_dump(),
    }

    save_json(
        bank_payload,
        filename=str(sector_bank_path(sector_name).name),
        directory=sector_dir,
    )

    return bank


def build_all_sectors(force: bool = False):
    sectors = load_sectors()
    for sector_name in sectors["sectors"]:
        print(f"\n{'='*50}")
        print(f"Building sector: {sector_name}")
        print(f"{'='*50}")
        build_sector_bank(sector_name, force=force)


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if args:
        for sector in args:
            build_sector_bank(sector, force=True)
    else:
        build_all_sectors()
