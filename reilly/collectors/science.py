"""Science & technology: arXiv preprints, OpenAlex publication trends and
Hacker News discussion (all public APIs, no keys)."""

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List

from ..http import get_json, get_text
from ..models import Article

ATOM = "{http://www.w3.org/2005/Atom}"


def arxiv(topic: str, limit: int = 15) -> List[Article]:
    text = get_text("https://export.arxiv.org/api/query", params={
        "search_query": f'all:"{topic}"', "max_results": limit,
        "sortBy": "submittedDate", "sortOrder": "descending",
    }, ttl=21600)
    out = []
    for e in ET.fromstring(text).iter(ATOM + "entry"):
        published = e.findtext(ATOM + "published") or ""
        try:
            ts = datetime.fromisoformat(published.replace("Z", "+00:00")).timestamp()
        except ValueError:
            ts = None
        out.append(Article(
            title=re.sub(r"\s+", " ", e.findtext(ATOM + "title") or "").strip(),
            url=(e.findtext(ATOM + "id") or "").strip(), source="arXiv", published=ts,
            lang="en", collector="arxiv", tier=2,
            snippet=re.sub(r"\s+", " ", e.findtext(ATOM + "summary") or "").strip()[:300],
        ))
    return out


def openalex_trend(topic: str) -> Dict[str, Any]:
    """Works per year for a topic; growth of the last full year vs the one before."""
    data = get_json("https://api.openalex.org/works", params={
        "search": topic, "group_by": "publication_year"}, ttl=86400)
    counts = {int(g["key"]): int(g["count"]) for g in data.get("group_by", [])
              if str(g.get("key", "")).isdigit()}
    this_year = datetime.now().year
    last, prev = counts.get(this_year - 1, 0), counts.get(this_year - 2, 0)
    years = sorted(y for y in counts if this_year - 6 <= y <= this_year - 1)
    return {"topic": topic, "by_year": {y: counts[y] for y in years},
            "last_full_year": last, "growth": round(last / prev - 1, 3) if prev else None}


def hackernews(topic: str, limit: int = 20) -> List[Article]:
    data = get_json("https://hn.algolia.com/api/v1/search_by_date", params={
        "query": topic, "tags": "story", "hitsPerPage": limit}, ttl=3600)
    return [Article(title=h.get("title") or "", url=h.get("url") or
                    f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                    source="Hacker News", published=h.get("created_at_i"), lang="en",
                    collector="hackernews", tier=3, snippet=f"points {h.get('points', 0)}")
            for h in data.get("hits", []) if h.get("title")]
