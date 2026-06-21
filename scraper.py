import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import MAX_PAGES, REQUEST_TIMEOUT

RELEVANT_KEYWORDS = [
    "help", "faq", "support", "docs", "documentation",
    "about", "about-us",
    "pricing", "plans",
    "blog", "resources",
    "contact", "contact-us",
    "terms", "privacy", "legal",
    "careers", "jobs",
    "features", "how-it-works",
    "api",
]

IGNORE_KEYWORDS = [
    "login", "signin", "signup", "register",
    "cart", "checkout", "shop",
    "facebook", "twitter", "instagram", "linkedin",
    "cdn.", "assets", "static", "images", "img",
    "download", ".zip", ".pdf", ".jpg", ".png",
]


def _score_url(path: str) -> int:
    path_lower = path.lower()
    for kw in RELEVANT_KEYWORDS:
        if kw in path_lower:
            return 10 - path_lower.count("/")
    return 0


def _should_ignore(url: str) -> bool:
    for kw in IGNORE_KEYWORDS:
        if kw in url.lower():
            return True
    return False


def _is_same_domain(base: str, url: str) -> bool:
    return urlparse(url).netloc == "" or urlparse(base).netloc in url


def _html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines[:500])


def discover_urls(base_url: str) -> list[str]:
    if not base_url.startswith("http"):
        base_url = "https://" + base_url
    try:
        resp = requests.get(base_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch {base_url}: {e}")
        return [base_url]

    links = set()
    for match in re.finditer(r'href=["\']([^"\']+)["\']', resp.text):
        raw = match.group(1)
        full = urljoin(base_url, raw)
        if _should_ignore(full):
            continue
        if _is_same_domain(base_url, full) and urlparse(full).netloc:
            links.add(full)

    scored = [(url, _score_url(urlparse(url).path)) for url in links]
    scored.sort(key=lambda x: -x[1])
    top = [url for url, s in scored if s > 0][:MAX_PAGES]

    if not top:
        top = [base_url]

    all_urls = [base_url] + [u for u in top if u != base_url]
    return list(dict.fromkeys(all_urls))


def _get_title(html: str, fallback: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.title
    return tag.string.strip() if tag and tag.string else fallback


def scrape_pages(urls: list[str]) -> dict[str, str]:
    results = {}
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    for url in urls:
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            text = _html_to_markdown(resp.text)
            title = _get_title(resp.text, url)
            if len(text) > 100:
                results[title] = text
                print(f"  [+] {title[:60]}")
            else:
                print(f"  [-] {title[:60]} (too short, skipped)")
        except Exception as e:
            print(f"  [x] {url[:60]}: {e}")
    return results
