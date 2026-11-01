"""Standing analysis profiles (profiles.json) and trusted feeds (sources.json).
Both files live in the project root and are meant to be edited by hand."""

import json
import re
from urllib.parse import urlparse
from typing import Any, Dict, List

from . import config, planner
from .models import Plan

PROFILES_FILE = config.ROOT / "profiles.json"
SOURCES_FILE = config.ROOT / "sources.json"
ORDER = ["war_ua", "eu_poland", "ua_politics", "economy", "crypto", "science_tech", "hazards"]


def _load(path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_profiles() -> Dict[str, Any]:
    return _load(PROFILES_FILE)


def all_feeds() -> Dict[str, Dict[str, Any]]:
    """Every feed in sources.json, switched off ones included."""
    return _load(SOURCES_FILE)["feeds"]


def save_feeds(feeds: Dict[str, Dict[str, Any]]) -> None:
    """Write sources.json keeping one feed per line, easy to edit by hand."""
    data = _load(SOURCES_FILE)
    lines = [f"    {json.dumps(fid)}: {json.dumps(f, ensure_ascii=False)}"
             for fid, f in feeds.items()]
    head = json.dumps(data.get("_help", ""), ensure_ascii=False)
    SOURCES_FILE.write_text('{\n  "_help": ' + head + ',\n  "feeds": {\n' +
                            ",\n".join(lines) + "\n  }\n}\n", encoding="utf-8")


def add_feed(name: str, url: str, lang: str, tier: int, tags: List[str],
             focused: bool = False) -> str:
    feeds = all_feeds()
    host = urlparse(url).netloc.lower().removeprefix("www.").split(".")[0]
    base = (re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            or re.sub(r"[^a-z0-9]+", "_", host).strip("_") or "feed")
    fid, n = base, 2
    while fid in feeds:
        fid, n = f"{base}_{n}", n + 1
    feeds[fid] = {"name": name, "url": url, "lang": lang, "tier": int(tier), "tags": tags}
    if focused:
        feeds[fid]["focused"] = True
    save_feeds(feeds)
    return fid


def profile_tags() -> Dict[str, str]:
    """Profile id -> its main feed tag (adding a feed to a profile = giving it this tag)."""
    return {pid: p["feed_tags"][0] for pid, p in load_profiles()["profiles"].items()
            if p.get("feed_tags")}


def load_feeds() -> Dict[str, Dict[str, Any]]:
    return {fid: {"id": fid, **f} for fid, f in _load(SOURCES_FILE)["feeds"].items()
            if f.get("enabled", True)}


def profile_ids() -> List[str]:
    found = list(load_profiles()["profiles"])
    return [p for p in ORDER if p in found] + [p for p in found if p not in ORDER]


def feeds_for(tags: List[str]) -> List[Dict[str, Any]]:
    """Feeds having any of the tags; 'focused' only counts for those tags."""
    out = []
    for f in load_feeds().values():
        hit = [t for t in f.get("tags", []) if t in tags]
        if hit:
            out.append({**f, "focused": bool(f.get("focused"))})
    return out


def trust_tiers() -> Dict[str, int]:
    """Source display name (lower case) -> tier, for news found via search."""
    return {f["name"].lower(): int(f.get("tier", 2)) for f in load_feeds().values()}


def build_plan(pid: str, lang: str, horizon_days: int = 30, hypothesis: str = "",
               polarity: str = "risk", prior: float = 0.5,
               asset_direction: str = "auto") -> Plan:
    data = load_profiles()
    prof = data["profiles"][pid]
    queries = dict(prof.get("queries", {}))
    langs = prof.get("langs") or list(queries) or [lang]
    topic = queries.get(lang) or queries.get("en") or next(iter(queries.values()), pid)
    plan = planner.build(
        topic, lang=lang, assets=prof.get("assets") or [], countries=prof.get("countries") or [],
        search_langs=langs, hypothesis=hypothesis, polarity=polarity, prior=prior,
        asset_direction=asset_direction, horizon_days=horizon_days, translate=False,
    )
    # hand-written queries per language are better than machine translation
    plan.search_queries = {lg: queries.get(lg) or plan.search_queries.get(lg, topic) for lg in langs}
    plan.profile = pid
    plan.domain = pid.upper()
    plan.assets = list(prof.get("assets", []))  # exactly as configured, no auto-detection
    plan.countries = list(prof.get("countries", []))
    plan.feeds = feeds_for(prof.get("feed_tags", []))
    plan.extras = list(prof.get("extras", []))
    plan.filter_keywords = [k.lower() for k in prof.get("keywords", [])]
    plan.keywords = list(dict.fromkeys(plan.filter_keywords + plan.keywords))[:60]
    plan.research_topics = list(prof.get("research_topics", []))
    if "weather" in plan.extras or "floods" in plan.extras or "air_quality" in plan.extras:
        plan.locations = list(data.get("locations", []))
    return plan
