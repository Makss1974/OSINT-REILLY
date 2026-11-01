"""Task mode: the analyst states a task in plain words; the agent picks
sources, collects, looks for gaps, searches once more and writes the analysis.

The model only plans and writes. Every number still comes from the
collectors and the analytics; without an LLM the plan is built by matching
the task against the profiles.
"""

import copy
import json
import re
from typing import Any, Callable, Dict, List, Tuple

from . import llm, pipeline, planner, profiles, reading, report
from .analytics import text as tx
from .http import FetchError
from .i18n import LANG_NAMES, LANGS, Translator
from .models import Plan

Progress = Callable[[str], None]

EXTRAS = {
    "war_losses": "daily Russian losses reported by the Ukrainian General Staff",
    "nbu_fx": "official UAH exchange rates (National Bank of Ukraine)",
    "nbu_rate": "NBU key policy rate",
    "nbp_fx": "official PLN exchange rates (National Bank of Poland)",
    "eurostat_hicp": "monthly inflation HICP for EU countries (Eurostat)",
    "fear_greed": "crypto Fear & Greed index",
    "defi_tvl": "DeFi total value locked",
    "stablecoins": "stablecoin supply",
    "arxiv": "arXiv preprints on research_topics",
    "openalex": "yearly publication trend on research_topics",
    "hackernews": "Hacker News technology discussion on research_topics",
    "weather": "10-day severe weather warnings for home locations (Poland, Ukraine)",
    "floods": "river flood forecast (GloFAS) for home locations",
    "air_quality": "air quality forecast for home locations",
    "gdacs": "current global disaster alerts (GDACS); only for disaster or climate tasks",
    "earthquakes": "recent significant earthquakes (USGS)",
    "eonet": "current natural events: wildfires, storms, volcanoes (NASA)",
    "space_weather": "geomagnetic storm forecast (NOAA)",
}
LOCAL_EXTRAS = {"weather", "floods", "air_quality"}
TICKER = re.compile(r"^[\w^=.\-]{1,15}$")
ISO2 = re.compile(r"^[A-Z]{2}$")


def _json(text: str) -> Dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the answer")
    return json.loads(text[start:end + 1])


def feed_tags() -> Dict[str, List[str]]:
    """Tag -> names of trusted outlets carrying it."""
    out: Dict[str, List[str]] = {}
    for f in profiles.load_feeds().values():
        for tag in f.get("tags", []):
            out.setdefault(tag, []).append(f["name"])
    return out


def _clean_spec(raw: Dict[str, Any], tags: Dict[str, List[str]]) -> Dict[str, Any]:
    """Keep only what exists in the catalogs; the model may hallucinate."""
    langs = [x for x in raw.get("langs", []) if x in LANGS][:4]
    queries = {k: " ".join(str(v).split()[:8]) for k, v in (raw.get("queries") or {}).items()
               if k in LANGS and str(v).strip()}
    langs = langs or list(queries)
    try:
        prior = min(max(float(raw.get("prior", 0.5)), 0.05), 0.95)
    except (TypeError, ValueError):
        prior = 0.5
    return {
        "reason": str(raw.get("reason", ""))[:300],
        "langs": langs,
        "queries": {k: v for k, v in queries.items() if k in langs},
        "keywords": [str(k).lower().strip() for k in raw.get("keywords", [])
                     if 2 < len(str(k).strip()) < 30][:30],
        "feed_tags": [t for t in raw.get("feed_tags", []) if t in tags],
        "extras": [e for e in raw.get("extras", []) if e in EXTRAS],
        "assets": [str(a).strip() for a in raw.get("assets", []) if TICKER.match(str(a).strip())][:6],
        "countries": [str(c).upper() for c in raw.get("countries", [])
                      if ISO2.match(str(c).upper())][:3],
        "research_topics": [str(x)[:60] for x in raw.get("research_topics", [])][:3],
        "hypothesis": str(raw.get("hypothesis", "") or "")[:200],
        "polarity": "positive" if str(raw.get("polarity", "")).startswith("p") else "risk",
        "asset_direction": raw.get("asset_direction") if raw.get("asset_direction") in ("up", "down")
        else "auto",
        "prior": prior,
    }


def _llm_spec(task: str, lang: str, horizon: int, tags: Dict[str, List[str]]) -> Dict[str, Any]:
    home = profiles.load_profiles().get("home_country", "")
    catalog_tags = "\n".join(f"- {t}: {', '.join(n[:6])}" for t, n in tags.items())
    catalog_extras = "\n".join(f"- {k}: {v}" for k, v in EXTRAS.items())
    text = llm.chat(
        "You plan an open-source intelligence collection. Choose sources only from the "
        "catalogs given. Answer with one JSON object only.",
        f"Task: {task}\nAnalyst language: {LANG_NAMES.get(lang, lang)} (write reason and "
        f"hypothesis in it). Analyst lives in: {home}. "
        f"Forecast horizon: {horizon} days.\n\n"
        f"RSS groups of trusted outlets (feed_tags):\n{catalog_tags}\n\n"
        f"Special data collectors (extras):\n{catalog_extras}\n\n"
        "JSON fields:\n"
        '"reason": one sentence why these sources fit the task,\n'
        f'"langs": 2-4 search languages from {list(LANGS)},\n'
        '"queries": {"<lang>": "2-5 word news search query in that language"},\n'
        '"keywords": 15-25 lowercase word stems in those languages to judge relevance,\n'
        '"feed_tags": [], "extras": [] (only from the catalogs, [] if none fit),\n'
        '"assets": Yahoo Finance tickers or crypto symbols, max 6, [] if markets do not matter,\n'
        '"countries": ISO2 codes for macro statistics, max 3,\n'
        '"research_topics": English topics, only if arxiv/openalex/hackernews are chosen,\n'
        '"hypothesis": one testable statement for the horizon, or "",\n'
        '"polarity": "risk" or "positive",\n'
        '"asset_direction": "up" or "down" = the move of the chosen tickers AS QUOTED that '
        'supports the hypothesis (USDUAH=X up = weaker hryvnia), "auto" if unsure,\n'
        '"prior": probability 0-1 of the hypothesis before evidence.',
        max_tokens=2500)
    return _clean_spec(_json(text), tags)


def _heuristic_spec(task: str, tags: Dict[str, List[str]]) -> Dict[str, Any]:
    """No LLM: borrow sources from the profiles whose vocabulary the task uses."""
    spec = {"reason": "", "langs": [], "queries": {}, "keywords": [], "feed_tags": [],
            "extras": [], "assets": [], "countries": [], "research_topics": [],
            "hypothesis": "", "polarity": "risk", "asset_direction": "auto", "prior": 0.5}
    matched = []
    for pid, prof in profiles.load_profiles()["profiles"].items():
        if tx.distinct_hits(task, [k.lower() for k in prof.get("keywords", [])]) >= 1:
            matched.append(pid)
            spec["feed_tags"] += [t for t in prof.get("feed_tags", []) if t in tags]
            spec["extras"] += [e for e in prof.get("extras", []) if e in EXTRAS]
            spec["countries"] += prof.get("countries", [])
    spec["feed_tags"] = list(dict.fromkeys(spec["feed_tags"]))
    spec["extras"] = list(dict.fromkeys(spec["extras"]))
    spec["countries"] = list(dict.fromkeys(spec["countries"]))[:3]
    spec["reason"] = "profiles matched: " + (", ".join(matched) or "none")
    return spec


def plan_task(task: str, lang: str, horizon: int = 30, use_llm: bool = True,
              progress: Progress = lambda s: None) -> Tuple[Plan, Dict[str, Any]]:
    base = planner.build(task, lang=lang, horizon_days=horizon, translate=False)
    tags = feed_tags()
    spec, note = None, ""
    if use_llm and llm.enabled():
        progress("LLM: plan")
        for _ in range(2):  # free models sometimes answer prose instead of JSON
            try:
                spec = _llm_spec(task, lang, horizon, tags)
                break
            except (FetchError, ValueError, KeyError) as exc:
                note = f"LLM plan failed, profiles used instead: {str(exc)[:120]}"
        if spec:
            note = ""
    if not spec:
        spec = _heuristic_spec(task, tags)

    plan = copy.deepcopy(base)
    if spec["queries"]:
        plan.search_langs = list(spec["queries"])
        plan.search_queries = dict(spec["queries"])
    if spec["assets"]:
        plan.assets = spec["assets"]
    if spec["countries"]:
        plan.countries = spec["countries"]
    plan.feeds = profiles.feeds_for(spec["feed_tags"])
    plan.extras = spec["extras"]
    plan.filter_keywords = spec["keywords"] or list(base.keywords)
    plan.keywords = list(dict.fromkeys(plan.filter_keywords + base.keywords))[:40]
    plan.research_topics = spec["research_topics"]
    if LOCAL_EXTRAS & set(plan.extras):
        plan.locations = list(profiles.load_profiles().get("locations", []))
    if spec["hypothesis"]:
        plan.hypothesis, plan.polarity = spec["hypothesis"], spec["polarity"]
        plan.asset_direction, plan.prior = spec["asset_direction"], spec["prior"]
    spec["note"] = note
    return plan, spec


def review(task: str, result: Dict[str, Any], tried: Dict[str, str],
           lang: str = "en") -> Dict[str, Any]:
    """Ask the model what the first collection misses; new queries if any."""
    stories = "\n".join(f"- {s['title']} ({s['sources']} sources)" for s in result["stories"][:15])
    have = [k for k in ("markets", "macro", "indicators", "hazards", "research") if result.get(k)]
    text = llm.chat(
        "You check whether collected news covers a research task. Answer with one JSON "
        "object only.",
        f"Task: {task}\n\nTop stories collected:\n{stories or '(none)'}\n\n"
        f"Data sections present: {', '.join(have) or 'news only'}\n"
        f"Queries already used: {json.dumps(tried, ensure_ascii=False)}\n\nReturn "
        '{"gap": "what important aspect is missing, one sentence in '
        f'{LANG_NAMES.get(lang, "English")}", '
        '"queries": {"<lang>": "new 2-5 word news query"}} with up to 3 languages from '
        f'{list(LANGS)} and queries different from those used, or '
        '{"gap": "", "queries": {}} if the coverage is sufficient.',
        max_tokens=1500)
    raw = _json(text)
    queries = {k: " ".join(str(v).split()[:8]) for k, v in (raw.get("queries") or {}).items()
               if k in LANGS and str(v).strip() and str(v).strip() != tried.get(k)}
    return {"gap": str(raw.get("gap", ""))[:300], "queries": dict(list(queries.items())[:3])}


def brief(task: str, result: Dict[str, Any], t: Translator) -> str:
    horizon = result["plan"]["horizon_days"]
    return llm.chat(
        f"You are a careful intelligence analyst. Write in {LANG_NAMES[t.lang]}. Use ONLY "
        "the report data; never invent numbers, dates or events, and say plainly when the "
        f"data does not support a conclusion. Every word, headings included, in "
        f"{LANG_NAMES[t.lang]}. Structure with short headings: 1) Answer to the "
        "task (2-4 sentences). 2) Key facts, each with its source headline. 3) Interpretation "
        f"and uncertainty. 4) Scenarios for the next {horizon} days with rough probabilities "
        "adding up to about 100%. 5) Signals to watch. Max 450 words, plain text.",
        f"Task: {task}\n\nReport:\n{report.to_markdown(result, t)[:14000]}",
        max_tokens=3500)


def run_task(task: str, lang: str, horizon: int = 30, use_llm: bool = True,
             record: bool = True, progress: Progress = lambda s: None,
             read_full: bool = True) -> Dict[str, Any]:
    t = Translator(lang)
    plan, spec = plan_task(task, lang, horizon, use_llm, progress)
    collected = pipeline.collect(plan, progress)
    agent: Dict[str, Any] = {"llm": bool(use_llm and llm.enabled()), "reason": spec["reason"],
                             "feed_tags": spec["feed_tags"], "extras": plan.extras,
                             "gap": "", "round2": {}, "note": spec.get("note", "")}

    if agent["llm"]:
        first = pipeline.analyze(plan, collected, use_llm=False, record_forecasts=False)
        try:
            progress("LLM: gaps")
            rev = review(task, first, plan.search_queries, lang)
            agent["gap"] = rev["gap"]
            if rev["queries"]:
                agent["round2"] = rev["queries"]
                extra = copy.deepcopy(plan)
                extra.search_langs, extra.search_queries = list(rev["queries"]), rev["queries"]
                extra.feeds, extra.extras, extra.assets, extra.countries = [], [], [], []
                extra.urls, extra.research_topics, extra.locations = [], [], []
                more = pipeline.collect_news(extra, progress)
                seen = {a.url for a in collected.articles}
                collected.articles += [a for a in more.articles if a.url not in seen]
                collected.errors += [e for e in more.errors if e not in collected.errors]
                for lg, q in rev["queries"].items():
                    old = plan.search_queries.get(lg)
                    plan.search_queries[lg] = f"{old} | {q}" if old else q
        except (FetchError, ValueError, KeyError) as exc:
            agent["note"] = (agent["note"] + f" LLM review failed: {str(exc)[:120]}").strip()

    result = pipeline.analyze(plan, collected, use_llm=False, record_forecasts=record)
    result["agent"] = agent
    if read_full:
        result["reading"] = reading.read_stories(result["stories"], lang, use_llm, progress)
        if result["reading"]["note"]:
            result["errors"].append(result["reading"]["note"])
    if agent["llm"]:
        progress("LLM: analysis")
        try:
            result["summary"] = brief(task, result, t)
        except (FetchError, ValueError) as exc:
            result["errors"].append(f"LLM: {str(exc)[:160]}")
    return result

