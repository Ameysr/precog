import warnings
warnings.filterwarnings("ignore")

from scraper import discover_urls, scrape_pages
from profiler import build_profile
from sectors import get_sector_for_business_type, load_sector_raw_reviews
from classifier import classify_reviews, build_test_suite
from taxonomy import get_intents_for_sector


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
    pages = scrape_pages(urls)
    profile = build_profile(pages, url)

    print(f"\n  Business: {profile.business_type}")
    print(f"  Personas: {[p.name for p in profile.personas]}")
    print(f"  Intents: {[i.name for i in profile.intents]}")

    print(f"\n{'='*50}")
    print(f"PHASE 2: Match to sector + load taxonomy")
    print(f"{'='*50}")

    sector = get_sector_for_business_type(profile.business_type) or get_sector_for_business_type(company_name)

    if sector:
        taxonomy_intents = get_intents_for_sector(sector, [i.name for i in profile.intents])
        raw = load_sector_raw_reviews(sector)
        print(f"  Sector: {sector} ({len(raw)} reviews)")
        print(f"  Granular intents in taxonomy: {len(taxonomy_intents)}")
        for t in taxonomy_intents:
            print(f"    [{t['id']}] {t['name']}")
    else:
        print("  No sector match. Cannot build test suite.")
        return

    if not raw:
        print("  No reviews. Run: python build_sector_banks.py <sector>")
        return

    print(f"\n{'='*50}")
    print(f"PHASE 3: Classify reviews against taxonomy")
    print(f"{'='*50}")

    classified = classify_reviews(sector, profile, sample_size=45)

    if not classified:
        print("  Classification failed.")
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
    print(f"  Coverage: {suite['coverage']['granular_intents']['pct']}% granular intents")
    print(f"  Failure modes tested: {suite['coverage']['failure_modes']['unique_tested']} unique")
    print(f"  Severity distribution: {suite['coverage']['by_severity']}")

    if suite["gaps"]["untested_intents"]:
        print(f"\n  Gaps: {', '.join(suite['gaps']['untested_intents'])}")
        print(f"  {suite['gaps']['recommendation']}")
    else:
        print(f"\n  Full intent coverage achieved.")

    print(f"\n  Output: output/{profile.company_name.lower().replace(' ', '-')}_test_suite.json")
    print(f"  Ready for Agnost's auto-fix pipeline.")


if __name__ == "__main__":
    main()
