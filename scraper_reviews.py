import json
import re
import time
import warnings
from pathlib import Path
from urllib.parse import urlparse

import cloudscraper
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel

from config import REQUEST_TIMEOUT
from utils import call_llm, save_json

warnings.filterwarnings("ignore", message=".*renamed to.*")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

_session_cloud = None


def _cloud() -> cloudscraper.CloudScraper:
    global _session_cloud
    if _session_cloud is None:
        _session_cloud = cloudscraper.create_scraper()
    return _session_cloud


class LanguageBank(BaseModel):
    vocabulary: dict
    sentence_starters: dict
    hinglish_examples: list[str]
    emotional_patterns: list[dict]
    real_complaints_cleaned: list[str]
    domain_issues: list[str]
    financial_terms: list[str]
    anger_words: list[str]
    panic_words: list[str]
    sarcasm_patterns: list[str]
    typos_common: list[str]


def _discover_app_id(company_url: str) -> str | None:
    try:
        resp = requests.get(
            company_url, timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "play.google.com/store/apps/details" in href and "id=" in href:
                match = re.search(r"id=([^&?]+)", href)
                if match:
                    app_id = match.group(1)
                    print(f"  [i] Found app ID from website: {app_id}")
                    return app_id
        return None
    except Exception as e:
        print(f"  [x] App ID discovery failed: {e}")
        return None


def scrape_google_play(app_id: str, count: int = 200) -> list[dict]:
    try:
        from google_play_scraper import reviews, Sort

        candidate_ids = [app_id]
        if not app_id.startswith("com."):
            candidate_ids = [f"com.{app_id}", app_id]

        for candidate in candidate_ids:
            try:
                result, _ = reviews(
                    candidate,
                    lang="en",
                    country="in",
                    sort=Sort.MOST_RELEVANT,
                    count=count,
                )
                if result:
                    reviews_list = []
                    for r in result:
                        reviews_list.append({
                            "source": "google_play",
                            "text": r.get("content", ""),
                            "rating": r.get("score", 0),
                            "date": str(r.get("at", "")),
                        })
                    print(f"  [+] Google Play ({candidate}): {len(reviews_list)} reviews")
                    return reviews_list
                print(f"  [-] Google Play ({candidate}): 0 reviews, trying next...")
            except Exception as e:
                print(f"  [-] Google Play ({candidate}): {e}")
                continue
        return []
    except ImportError:
        print("  [!] google-play-scraper not installed, skipping Google Play")
        return []


def scrape_trustpilot(domain: str, count: int = 50) -> list[dict]:
    results = []
    urls = [
        f"https://www.trustpilot.com/review/{domain}",
        f"https://www.trustpilot.com/review/www.{domain}",
    ]
    seen = set()
    for url in urls:
        try:
            resp = _cloud().get(url, timeout=REQUEST_TIMEOUT + 5)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for card in soup.select('[data-service-review-card]'):
                text_el = card.select_one('[data-service-review-text-typography]')
                rating_el = card.select_one('[data-service-review-rating]')
                if text_el:
                    text = text_el.get_text(strip=True)
                    if text and text not in seen:
                        seen.add(text)
                        results.append({
                            "source": "trustpilot",
                            "text": text,
                            "rating": int(rating_el.get("data-service-review-rating", 0)) if rating_el else 0,
                        })
            if len(results) >= count:
                break
            time.sleep(0.5)
        except Exception:
            pass
    if results:
        print(f"  [+] Trustpilot: {len(results)} reviews")
    else:
        print(f"  [-] Trustpilot: blocked / no reviews found")
    return results[:count]


def scrape_web_search(company_name: str, full_name: str = "", count: int = 30) -> list[dict]:
    results = []
    seen = set()
    name = full_name or company_name
    queries = [
        f"{name} review complaint",
        f"{name} customer support issue",
        f"{name} problem",
        f"{name} bad experience",
        f'{company_name} "worst" review',
    ]
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        for query in queries:
            try:
                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=10):
                        snippet = r.get("body", "") or r.get("snippet", "")
                        title = r.get("title", "")
                        text = f"{title}: {snippet}"
                        if text and text not in seen and len(text) > 30:
                            seen.add(text)
                            results.append({
                                "source": "web_search",
                                "text": text[:500],
                                "rating": 0,
                            })
                if len(results) >= count:
                    break
            except Exception:
                pass
    except ImportError:
        print("  [!] duckduckgo_search not installed, skipping web search")
        return []
    if results:
        print(f"  [+] Web search: {len(results)} reviews")
    else:
        print(f"  [-] Web search: no results found")
    return results[:count]


def scrape_reddit(company_name: str, count: int = 50) -> list[dict]:
    results = []
    seen = set()
    queries = [
        company_name,
        f"{company_name} complaint",
        f"{company_name} issue",
        f"{company_name} scam",
    ]
    for query in queries:
        try:
            encoded = requests.utils.quote(query)
            url = f"https://old.reddit.com/search?q={encoded}&sort=top&t=year"
            resp = _cloud().get(
                url, timeout=REQUEST_TIMEOUT + 5,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for post in soup.select("div.thing"):
                title_el = post.select_one("a.title")
                if title_el:
                    title = title_el.get_text(strip=True)
                    if title and title not in seen and len(title) > 20:
                        seen.add(title)
                        results.append({
                            "source": "reddit",
                            "text": title,
                            "rating": 0,
                        })
            if len(results) >= count:
                break
            time.sleep(0.5)
        except Exception:
            pass
    if results:
        print(f"  [+] Reddit: {len(results)} reviews")
    else:
        print(f"  [-] Reddit: blocked / no reviews found")
    return results[:count]


def _extract_domain(company_url: str) -> str:
    parsed = urlparse(company_url)
    domain = parsed.netloc or parsed.path
    domain = re.sub(r"^www\.", "", domain)
    return domain


def _clean_review_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1000]


def build_language_bank(
    company_name: str,
    raw_reviews: list[dict],
) -> LanguageBank:
    combined = "\n\n".join(
        f"[{r['source']}] (rating {r['rating']}): {r['text']}"
        for r in raw_reviews[:200]
    )

    prompt = f"""You are analyzing real user reviews for {company_name}.

Here are {len(raw_reviews)} real reviews from Google Play, Trustpilot, and Reddit:

{combined[:12000]}

Extract a structured language bank to help generate realistic synthetic user conversations.
Focus on capturing the MESSY, REAL patterns — not sanitized versions.

Extract:
1. vocabulary: dict with keys "anger_words", "panic_words", "sarcasm_phrases", "hinglish_phrases", each as list of examples
2. sentence_starters: dict with keys "angry", "panicked", "confused", "sarcastic", each as list of real sentence starters
3. hinglish_examples: list of real Hinglish phrases found (exact matches)
4. emotional_patterns: list of dicts with "emotion" and "example_text"
5. real_complaints_cleaned: list of 20 most representative complaint texts (cleaned but keep emotional language)
6. domain_issues: list of specific issues users repeatedly face
7. financial_terms: list of financial specific terms found (amounts, order types, error codes)
8. anger_words: list of actual anger/vulgar words used
9. panic_words: list of words indicating financial panic
10. sarcasm_patterns: list of sarcastic phrases used
11. typos_common: list of common typos/autocorrect fails found

Return ONLY valid JSON matching the schema."""

    return call_llm(prompt, LanguageBank)


def _generate_fallback_bank(company_name: str, profile=None) -> LanguageBank:
    from profiler import CompanyProfile

    domain_hint = f" ({profile.business_type})" if profile else ""
    personas_text = ""
    intents_text = ""
    issues_text = ""
    terms_text = ""

    if profile:
        personas_text = "\n".join(f"  - {p.name}: {p.description}" for p in profile.personas)
        intents_text = "\n".join(f"  - {i.name}: {i.description}" for i in profile.intents)
        issues_text = "\n".join(f"  - {a}" for a in (profile.high_frustration_areas + profile.known_issues_from_docs + profile.error_scenarios)[:8])
        terms_text = ", ".join(profile.domain_terminology[:8]) if profile.domain_terminology else ""

    schema = json.dumps({
        "vocabulary": {"anger_words": ["word1", "word2"], "panic_words": ["word1"], "sarcasm_phrases": ["phrase1"], "hinglish_phrases": ["phrase1"]},
        "sentence_starters": {"angry": ["starter1"], "panicked": ["starter1"], "confused": ["starter1"], "sarcastic": ["starter1"]},
        "hinglish_examples": ["phrase1", "phrase2"],
        "emotional_patterns": [{"emotion": "anger", "example_text": "text"}],
        "real_complaints_cleaned": ["complaint1", "complaint2"],
        "domain_issues": ["issue1", "issue2"],
        "financial_terms": ["term1", "term2"],
        "anger_words": ["word1", "word2"],
        "panic_words": ["word1", "word2"],
        "sarcasm_patterns": ["pattern1", "pattern2"],
        "typos_common": ["typo1", "typo2"],
    }, indent=2)

    prompt = f"""Generate a language bank for {company_name}{domain_hint}.

This company serves these customer types:
{personas_text}

Customers commonly need help with:
{intents_text}

Known issues / frustration areas from the company's own help center:
{issues_text}

Domain-specific terminology: {terms_text}

Since no real user reviews were available, create a realistic language bank based on the above company profile.
Generate complaints that match their actual business — use their specific terminology, reference their known issues, and match their customer types.

Return ONLY valid JSON matching this EXACT schema (field names must be identical):
{schema}

Make it feel REAL — not polite, not sanitized. Model it after real complaints on Trustpilot/Reddit.
Fill each list with 5-15 real examples. Do NOT skip any fields."""

    return call_llm(prompt, LanguageBank)


def scrape_all(
    company_name: str,
    company_url: str,
    app_id: str | None = None,
    profile=None,
) -> LanguageBank:
    domain = _extract_domain(company_url)

    if not app_id:
        app_id = _discover_app_id(company_url)

    print("[reviews] Scraping Google Play...")
    play_reviews = scrape_google_play(app_id) if app_id else []
    time.sleep(1)

    print("[reviews] Scraping Trustpilot...")
    trust_reviews = scrape_trustpilot(domain)
    time.sleep(1)

    print("[reviews] Scraping Reddit...")
    reddit_reviews = scrape_reddit(company_name)

    full_company_name = getattr(profile, "company_name", company_name) if profile else company_name
    print("[reviews] Scraping web search...")
    web_reviews = scrape_web_search(company_name, full_name=full_company_name)

    all_reviews = play_reviews + trust_reviews + reddit_reviews + web_reviews
    print(f"[reviews] Total raw reviews: {len(all_reviews)}")

    if not all_reviews:
        print("[!] No reviews found from any source. Generating synthetic language bank from industry profile...")
        bank = _generate_fallback_bank(company_name, profile=profile)
        bank_payload = {
            "company": company_name,
            "total_reviews": 0,
            **bank.model_dump(),
        }
        save_json(
            bank_payload,
            filename=f"{company_name.lower().replace(' ', '-')}_language_bank.json",
        )
        return bank

    for r in all_reviews:
        r["text"] = _clean_review_text(r["text"])

    save_json(
        {"company": company_name, "total": len(all_reviews), "reviews": all_reviews},
        filename=f"{company_name.lower().replace(' ', '-')}_raw_reviews.json",
    )

    print("[reviews] Building language bank...")
    bank = build_language_bank(company_name, all_reviews)

    bank_payload = {
        "company": company_name,
        "total_reviews": len(all_reviews),
        **bank.model_dump(),
    }
    save_json(
        bank_payload,
        filename=f"{company_name.lower().replace(' ', '-')}_language_bank.json",
    )

    return bank


def main():
    import sys
    args = sys.argv[1:]
    if len(args) < 2:
        print("Usage: python scraper_reviews.py <company_name> <company_url> [app_id]")
        return
    company_name = args[0]
    company_url = args[1]
    app_id = args[2] if len(args) > 2 else None
    bank = scrape_all(company_name, company_url, app_id)
    if bank:
        print(f"Done. Language bank saved.")
    else:
        print("Failed to build language bank.")


if __name__ == "__main__":
    main()
