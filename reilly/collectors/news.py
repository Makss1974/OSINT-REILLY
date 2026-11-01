"""News collectors: Google News RSS (public feed) and GDELT DOC 2.0 API."""

import email.utils
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Tuple

from ..http import get_json, get_text
from ..models import Article, Series

# hl / gl / ceid per interface language
GNEWS_EDITIONS = {
    "en": ("en-US", "US", "US:en"),
    "uk": ("uk", "UA", "UA:uk"),
    "de": ("de", "DE", "DE:de"),
    "fr": ("fr", "FR", "FR:fr"),
    "es": ("es", "ES", "ES:es"),
    "it": ("it", "IT", "IT:it"),
    "pl": ("pl", "PL", "PL:pl"),
}
GDELT_LANG = {
    "en": "english", "uk": "ukrainian", "de": "german", "fr": "french",
    "es": "spanish", "it": "italian", "pl": "polish",
}
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_TAG = re.compile(r"<[^>]+>")


def google_news(query: str, lang: str, days: int = 30, limit: int = 60) -> List[Article]:
    hl, gl, ceid = GNEWS_EDITIONS.get(lang, GNEWS_EDITIONS["en"])
    q = f"{query} when:{days}d" if days else query
    text = get_text(
        "https://news.google.com/rss/search",
        params={"q": q, "hl": hl, "gl": gl, "ceid": ceid},
        ttl=1800,
    )
    root = ET.fromstring(text)
    out: List[Article] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        source_el = item.find("source")
        source = (source_el.text or "").strip() if source_el is not None else ""
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3]
        published = None
        if item.findtext("pubDate"):
            try:
                published = email.utils.parsedate_to_datetime(item.findtext("pubDate")).timestamp()
            except (TypeError, ValueError):
                pass
        snippet = html.unescape(_TAG.sub(" ", item.findtext("description") or ""))
        out.append(Article(
            title=html.unescape(title),
            url=item.findtext("link") or "",
            source=source or "news.google.com",
            published=published,
            lang=lang,
            collector="google_news_rss",
            snippet=re.sub(r"\s+", " ", snippet).strip()[:300],
        ))
        if len(out) >= limit:
            break
    return out


def _gdelt_query(query: str, lang: str) -> str:
    # GDELT accepts parentheses only around OR-groups; plain words are AND-ed
    q = query.replace("(", " ").replace(")", " ").strip()
    if lang in GDELT_LANG:
        q += f" sourcelang:{GDELT_LANG[lang]}"
    return q


def gdelt_articles(query: str, lang: str, days: int = 30, limit: int = 75) -> List[Article]:
    data = get_json(GDELT_URL, params={
        "query": _gdelt_query(query, lang), "mode": "ArtList", "format": "json",
        "maxrecords": limit, "timespan": f"{days}d", "sort": "DateDesc",
    }, ttl=3600)
    out = []
    for a in data.get("articles", []) if isinstance(data, dict) else []:
        published = None
        try:
            published = datetime.strptime(a.get("seendate", ""), "%Y%m%dT%H%M%SZ").replace(
                tzinfo=timezone.utc).timestamp()
        except ValueError:
            pass
        out.append(Article(
            title=a.get("title", ""), url=a.get("url", ""), source=a.get("domain", ""),
            published=published, lang=lang, collector="gdelt",
        ))
    return out


def gdelt_timelines(query: str, lang: str, days: int = 90) -> Tuple[Series, Series]:
    """Daily coverage volume (share of all monitored news) and average tone."""
    result = []
    for mode, kind, unit in (("TimelineVolRaw", "news_volume", "articles"),
                             ("TimelineTone", "news_tone", "tone")):
        data = get_json(GDELT_URL, params={
            "query": _gdelt_query(query, lang), "mode": mode, "format": "json",
            "timespan": f"{days}d", "timelinesmooth": 0,
        }, ttl=3600)
        points = []
        for line in data.get("timeline", []) if isinstance(data, dict) else []:
            points = line.get("data", [])
            break
        dates = [p["date"][:8] for p in points]
        values = [float(p.get("value", 0.0)) for p in points]
        if kind == "news_volume" and dates:
            # aggregate to days (the API may return 15-min bins for short spans)
            agg = {}
            for d, v in zip(dates, values):
                agg[d] = agg.get(d, 0.0) + v
            dates, values = list(agg), list(agg.values())
        result.append(Series(f"GDELT {kind} [{lang}]", kind, dates, values, unit, "gdelt"))
    return result[0], result[1]
