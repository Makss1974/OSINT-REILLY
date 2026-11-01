"""Full text of news articles: polite download (robots.txt respected, cache,
per-host pauses) and plain-text extraction without extra libraries.

Order of extraction: schema.org articleBody (JSON-LD) -> paragraphs inside
<article> -> all paragraphs of the page. Paywalled or script-only pages give
little text and are reported as such, never worked around.
"""

import html
import json
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

from ..http import get_text

MIN_CHARS = 400        # less than this = paywall, consent page or video
MAX_CHARS = 6000       # enough for the facts, keeps the LLM prompt small
SKIP_HOSTS = ("news.google.com",)  # redirect pages without the article itself
# service lines some outlets put in every article
BOILERPLATE = ("Посилання для територій", "Links for territories", "Читайте також",
               "Read also", "Підписуйтесь", "Subscribe")

_LD = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)
_ARTICLE = re.compile(r"<article\b.*?</article>", re.S | re.I)
_P = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_JUNK = re.compile(r"<(script|style|noscript|svg|figure|aside|nav|footer)\b.*?</\1>", re.S | re.I)


def readable(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return url.startswith(("http://", "https://")) and not any(h in host for h in SKIP_HOSTS)


def _clean(fragment: str) -> str:
    return " ".join(html.unescape(_TAG.sub(" ", fragment)).split())


def _ld_body(page: str) -> str:
    for block in _LD.findall(page):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data])
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("articleBody"), str):
                return _clean(item["articleBody"])
    return ""


def extract(page: str) -> str:
    """Article text from an HTML page ('' if nothing readable)."""
    body = _ld_body(page)
    if len(body) >= MIN_CHARS:
        return body[:MAX_CHARS]
    page = _JUNK.sub(" ", page)
    scope = " ".join(_ARTICLE.findall(page)) or page
    paragraphs = [_clean(p) for p in _P.findall(scope)]
    text = "\n".join(p for p in paragraphs
                     if len(p) > 40 and not p.startswith(BOILERPLATE))
    return text[:MAX_CHARS]


def fetch(url: str) -> Dict[str, Any]:
    """{url, chars, text} — raises FetchError (robots, HTTP) like other collectors."""
    text = extract(get_text(url, ttl=6 * 3600, retries=2, check_robots=True))
    return {"url": url, "chars": len(text), "text": text if len(text) >= MIN_CHARS else ""}


def sentences_with_facts(text: str, limit: int = 3) -> List[str]:
    """Without an LLM: sentences carrying numbers or dates are the likeliest facts."""
    found = []
    for s in re.split(r"(?<=[.!?])\s+", text):
        s = s.strip()
        if 40 < len(s) < 300 and re.search(r"\d", s):
            found.append(s)
        if len(found) >= limit:
            break
    return found
