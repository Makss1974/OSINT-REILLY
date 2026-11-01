"""Public attention: Wikipedia search + daily pageviews (Wikimedia REST API)."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

from ..analytics import text as tx
from ..http import get_json
from ..models import Series


def find_article(query: str, lang: str, min_overlap: float = 0.5) -> Optional[str]:
    """Best search hit whose title really matches the query (else None:
    an unrelated article would give a misleading attention signal)."""
    data = get_json(f"https://{lang}.wikipedia.org/w/api.php", params={
        "action": "query", "list": "search", "srsearch": query,
        "format": "json", "srlimit": 5,
    }, ttl=86400)
    terms = tx.keywords(query, 8)
    for hit in data.get("query", {}).get("search", []):
        if tx.stem_overlap(terms, hit["title"]) >= min_overlap:
            return hit["title"]
    return None


def pageviews(title: str, lang: str, days: int = 120) -> Series:
    end = datetime.now(timezone.utc) - timedelta(days=1)
    start = end - timedelta(days=days)
    article = quote(title.replace(" ", "_"), safe="")
    data = get_json(
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"{lang}.wikipedia/all-access/user/{article}/daily/"
        f"{start:%Y%m%d}/{end:%Y%m%d}", ttl=21600,
    )
    items = data.get("items", [])
    return Series(f"Wikipedia [{lang}] {title}", "attention",
                  [i["timestamp"][:8] for i in items], [float(i["views"]) for i in items],
                  "views/day", "wikimedia")
