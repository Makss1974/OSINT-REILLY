"""Bright Data SERP API (optional, paid). Used only when a valid token and
SERP zone are configured in .env; returns organic Google results."""

from typing import List
from urllib.parse import quote_plus, urlparse

from .. import config
from ..http import FetchError, post_json
from ..models import Article


def enabled() -> bool:
    return bool(config.BRIGHTDATA_TOKEN and config.BRIGHTDATA_SERP_ZONE)


def serp(query: str, lang: str, country: str = "") -> List[Article]:
    if not enabled():
        raise FetchError("brightdata: BRIGHTDATA_API_TOKEN / BRIGHTDATA_SERP_ZONE not set")
    url = f"https://www.google.com/search?q={quote_plus(query)}&hl={lang}&num=20&brd_json=1"
    if country:
        url += f"&gl={country.lower()}"
    data = post_json(
        "https://api.brightdata.com/request",
        {"zone": config.BRIGHTDATA_SERP_ZONE, "url": url, "format": "raw"},
        {"Authorization": f"Bearer {config.BRIGHTDATA_TOKEN}"},
    )
    out = []
    for item in data.get("organic", []) if isinstance(data, dict) else []:
        link = item.get("link", "")
        out.append(Article(
            title=item.get("title", ""), url=link,
            source=item.get("display_link") or urlparse(link).netloc,
            published=None, lang=lang, collector="brightdata_serp",
            snippet=item.get("description", "")[:300],
        ))
    return out
