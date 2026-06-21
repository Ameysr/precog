import warnings
warnings.filterwarnings("ignore")

from scraper import discover_urls, scrape_pages
from profiler import build_profile
from sectors import get_sector_for_business_type, load_sector_raw_reviews
from classifier import classify_reviews, build_test_suite
from config import DEFAULT_COUNT


def main():
    url = input("Enter company URL: ").strip()
    if not url.startswith("http"):
        url = "https://" + url

    import re
    domain = url.split("//")[-1].split("/")[0]
    domain = re.sub(r"^www\.", "", domain)
    company_name = domain.split(".")[0].capitalize()
    name_hint = input(f"Company name [{company_name}]: ").strip()
    if name_hint:
        company_name = name_hint

    print(f"\n{'='*50}")
    print(f"PHASE 1: Understand the company")
    print(f"{'='*50}")
    urls = discover_urls(url)
    print(f"  Found {len(urls)} relevant pages")
    pages = scrape_pages(urls)
    print(f"  Scraped {len(pages)} pages")

    profile = build_profile(pages, url)
    print(f"\n  Business: {profile.business_type}")
    print(f"  Personas ({len(profile.personas)}): {[p.name for p in profile.personas]}")
    print(f"  Intents ({len(profile.intents)}): {[i.name for i in profile.intents]}")
    print(f"  Known issues: {profile.known_issues_from_docs[:4]}")

    print(f"\n{'='*50}")
    print(f"PHASE 2: Match to sector library")
    print(f"{'='*50}")

    sector = get_sector_for_business_type(profile.business_type)
    if not sector:
        sector = get_sector_for_business_type(company_name)

    if sector:
        raw = load_sector_raw_reviews(sector)
        print(f"  Sector detected: {sector} ({len(raw)} raw reviews available)")
    else:
        raw = []
        print(f"  No sector match found")

    if not raw:
        print("  [!] No reviews available. Cannot build test suite.")
        print("  Run: python build_sector_banks.py <sector_name> to add sector data")
        return

    print(f"\n{'='*50}")
    print(f"PHASE 3: Classify reviews by persona, intent, severity")
    print(f"{'='*50}")

    classified = classify_reviews(sector, profile, sample_size=min(DEFAULT_COUNT * 3, 100))

    if not classified:
        print("  [!] Classification failed. Try again later.")
        return

    print(f"\n{'='*50}")
    print(f"PHASE 4: Build structured test suite")
    print(f"{'='*50}")

    suite = build_test_suite(classified, profile)

    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")
    print(f"  Company: {profile.company_name}")
    print(f"  Sector: {sector}")
    print(f"  Reviews classified: {len(classified)}")
    print(f"  Test suite saved: output/{profile.company_name.lower().replace(' ', '-')}_test_suite.json")
    print(f"  Coverage: {suite['coverage']['intents']['pct']}% intents, {suite['coverage']['personas']['pct']}% personas")

    if suite["gaps"]["untested_intents"]:
        print(f"\n  [!] GAPS DETECTED")
        print(f"  Untested intents: {', '.join(suite['gaps']['untested_intents'])}")
        print(f"  Untested personas: {', '.join(suite['gaps']['untested_personas'])}")
        print(f"  Recommendation: {suite['gaps']['recommendation']}")
    else:
        print(f"\n  [OK] Full coverage achieved. Test suite ready for Agnost.")


if __name__ == "__main__":
    main()
