import warnings
warnings.filterwarnings("ignore")

from scraper import discover_urls, scrape_pages
from profiler import build_profile
from scraper_reviews import scrape_all as scrape_reviews
from generator import generate_conversations
from config import DEFAULT_COUNT


def main():
    url = input("Enter company URL: ").strip()
    if not url.startswith("http"):
        url = "https://" + url

    company_name = url.split("//")[-1].split(".")[0].capitalize()
    name_hint = input(f"Company name [{company_name}]: ").strip()
    if name_hint:
        company_name = name_hint

    app_hint = input("Google Play app ID (optional, press Enter to auto-discover): ").strip()

    print(f"\n{'='*50}")
    print(f"PHASE 1: Scrape website content")
    print(f"{'='*50}")
    urls = discover_urls(url)
    print(f"  Found {len(urls)} relevant pages")
    pages = scrape_pages(urls)
    print(f"  Scraped {len(pages)} pages")

    print(f"\n{'='*50}")
    print(f"PHASE 2: Build company profile")
    print(f"{'='*50}")
    profile = build_profile(pages, url)
    print(f"  Business: {profile.business_type}")
    print(f"  Personas: {[p.name for p in profile.personas]}")
    print(f"  Intents: {[i.name for i in profile.intents]}")
    print(f"  Domains issues from docs: {profile.known_issues_from_docs[:4]}")

    print(f"\n{'='*50}")
    print(f"PHASE 3: Scrape real user reviews")
    print(f"{'='*50}")
    bank = scrape_reviews(
        company_name=company_name,
        company_url=url,
        app_id=app_hint or None,
    )
    if bank:
        print(f"  Language bank built with real user vocabulary")
    else:
        print(f"  No reviews found. Continuing with profile-only generation.")

    print(f"\n{'='*50}")
    print(f"PHASE 4: Generate synthetic conversations")
    print(f"{'='*50}")
    result = generate_conversations(profile, count=DEFAULT_COUNT)
    print(f"  Done! {result['total']} conversations generated")
    print(f"  Ready to feed into Agnost")


if __name__ == "__main__":
    main()
