"""Generic RSS 2.0 / Atom / RDF reader for the feeds listed in sources.json."""

import email.utils
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..analytics import text as tx
from ..http import get_text
from ..models import Article

_TAG = re.compile(r"<[^>]+>")
_DECL = re.compile(r"^<\?xml[^>]*\?>")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(el: ET.Element, name: str) -> Optional[ET.Element]:
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _text(el: ET.Element, *names: str) -> str:
    for n in names:
        c = _child(el, n)
        if c is not None and (c.text or "").strip():
            return c.text.strip()
    return ""


def _date(value: str) -> Optional[float]:
    if not value:
        return None
    try:
        return email.utils.parsedate_to_datetime(value).timestamp()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _clean(value: str, limit: int = 300) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", value or ""))).strip()[:limit]


def parse(xml_text: str, feed: Dict[str, Any]) -> List[Article]:
    # the body is already decoded text: drop the declaration with its encoding
    root = ET.fromstring(_DECL.sub("", xml_text.lstrip("﻿ \r\n\t"), count=1))
    items = [el for el in root.iter() if _local(el.tag) in ("item", "entry")]
    out = []
    for it in items:
        link = _text(it, "link")
        if not link:  # Atom: <link href="..."/>
            el = _child(it, "link")
            link = el.get("href", "") if el is not None else ""
        out.append(Article(
            title=_clean(_text(it, "title"), 400),
            url=link,
            source=feed.get("name", feed.get("id", "")),
            published=_date(_text(it, "pubDate", "published", "updated", "date")),
            lang=feed.get("lang", ""),
            collector="rss",
            snippet=_clean(_text(it, "description", "summary", "encoded")),
            tier=int(feed.get("tier", 2)),
        ))
    return out


def relevant(article: Article, keywords: List[str]) -> bool:
    if not keywords:
        return True
    body = f"{article.title} {article.snippet}"
    return tx.count_stems(body, keywords) > 0


def read_feed(feed: Dict[str, Any], keywords: List[str], max_age_days: float = 14,
              now: float = 0.0) -> List[Article]:
    items = parse(get_text(feed["url"], ttl=1200), feed)
    if not feed.get("focused"):
        items = [a for a in items if relevant(a, keywords)]
    if now:
        items = [a for a in items if not a.published or now - a.published <= max_age_days * 86400]
    return items
