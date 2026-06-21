import warnings
warnings.filterwarnings("ignore")

from scraper import discover_urls, scrape_pages
from profiler import build_profile
from generator import generate_conversations
from config import DEFAULT_COUNT


def main():
    url = input("Enter company URL: ").strip()
    if not url.startswith("http"):
        url = "https://" + url

    print("\n[scraper] Discovering pages...")
    urls = discover_urls(url)
    print(f"  Found {len(urls)} relevant pages")

    print("[scraper] Scraping content...")
    pages = scrape_pages(urls)
    print(f"  Scraped {len(pages)} pages")

    print("[profiler] Building company profile...")
    profile = build_profile(pages, url)
    print(f"  Business: {profile.business_type}")
    print(f"  Personas: {[p.name for p in profile.personas]}")
    print(f"  Intents: {[i.name for i in profile.intents]}")

    print(f"[generator] Generating {DEFAULT_COUNT} conversations...")
    result = generate_conversations(profile, count=DEFAULT_COUNT)
    print(f"  Done! {result['total']} conversations generated")
    print(f"  Ready to feed into Agnost")


if __name__ == "__main__":
    main()
