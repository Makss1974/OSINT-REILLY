"""Blocks 2-4: collect open data for a plan and run the analytics."""

import json
import logging
import time
from typing import Any, Callable, Dict, List

from . import journal, llm, profiles, reading
from .analytics import hazards as hz
from .analytics import logic, market, signals, timeseries
from .collectors import (brightdata, crypto, hazards, macro, markets, news, official, pages,
                         rss, science, wiki)
from .http import FetchError
from .i18n import LANG_NAMES
from .models import Article, Collected, Plan, Series
from .planner import STATICITY

log = logging.getLogger(__name__)
Progress = Callable[[str], None]


def _try(store: Collected, label: str, fn, *args, **kwargs):
    try:
        result = fn(*args, **kwargs)
        if label not in store.sources_used:
            store.sources_used.append(label)
        return result
    except (FetchError, ValueError, KeyError) as exc:
        message = f"{label}: {str(exc)[:160]}"
        if message not in store.errors:
            store.errors.append(message)
        log.warning("%s failed: %s", label, exc)
        return None


def _dedupe(articles: List[Article]) -> List[Article]:
    seen, unique = set(), []
    for a in articles:
        key = a.url or a.title.lower()
        if a.title and key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


def collect_news(plan: Plan, progress: Progress = lambda s: None) -> Collected:
    """Search engines only (Google News, GDELT, Bright Data) for the plan queries."""
    c = Collected()
    articles: List[Article] = []
    for lang in plan.search_langs:
        q = plan.search_queries.get(lang, plan.topic)
        progress(f"Google News [{lang}]: {q}")
        articles += _try(c, "Google News RSS", news.google_news, q, lang) or []
        progress(f"GDELT [{lang}]: {q}")
        articles += _try(c, "GDELT", news.gdelt_articles, q, lang) or []
        if brightdata.enabled():
            progress(f"Bright Data SERP [{lang}]")
            articles += _try(c, "Bright Data SERP", brightdata.serp, q, lang) or []
    c.articles = _dedupe(articles)
    return c


def collect(plan: Plan, progress: Progress = lambda s: None) -> Collected:
    c = collect_news(plan, progress)
    articles: List[Article] = list(c.articles)
    now = time.time()
    for feed in plan.feeds:
        progress(f"RSS: {feed['name']}")
        articles += _try(c, f"RSS {feed['name']}", rss.read_feed, feed,
                         plan.filter_keywords, 14, now) or []
    if "arxiv" in plan.extras or "hackernews" in plan.extras:
        for topic in plan.research_topics:
            progress(f"arXiv / Hacker News: {topic}")
            if "arxiv" in plan.extras:
                articles += _try(c, "arXiv", science.arxiv, topic, 10) or []
            if "hackernews" in plan.extras:
                articles += _try(c, "Hacker News", science.hackernews, topic, 10) or []

    c.articles = _dedupe(articles)

    en_q = plan.search_queries.get("en", plan.topic)
    progress("GDELT timelines")
    timelines = _try(c, "GDELT", news.gdelt_timelines, en_q, "", 90)
    if timelines:
        c.series += [s for s in timelines if s.values]

    # profile queries are keyword bags: only English Wikipedia matches them reliably
    wiki_langs = ["en"] if plan.profile else list(dict.fromkeys([plan.lang, "en"]))
    for lang in wiki_langs if plan.profile != "hazards" else []:
        progress(f"Wikipedia [{lang}]")
        title = _try(c, "Wikipedia", wiki.find_article, plan.search_queries.get(lang, en_q), lang)
        if title:
            pv = _try(c, "Wikimedia pageviews", wiki.pageviews, title, lang)
            if pv and pv.values:
                c.series.append(pv)

    for asset in plan.assets:
        progress(f"{asset}")
        s = _try(c, "Markets", markets.price_history, asset)
        if s:
            c.series.append(s)

    for iso in plan.countries:
        progress(f"World Bank {iso}")
        for code in macro.INDICATORS:
            s = _try(c, "World Bank", macro.world_bank, iso, code)
            if s and s.values:
                c.series.append(s)

    for url in plan.urls:
        progress(f"Page {url}")
        r = _try(c, "Page monitor", pages.check_page, url)
        c.pages.append(r or {"url": url, "status": "ERROR"})
    _collect_extras(plan, c, progress)
    return c


def _collect_extras(plan: Plan, c: Collected, progress: Progress) -> None:
    """Special collectors named in the profile ("extras")."""
    ex = set(plan.extras)

    def series(label: str, fn, *args) -> None:
        progress(label)
        got = _try(c, label, fn, *args)
        for s in (got if isinstance(got, list) else [got] if got else []):
            if s.values:
                c.series.append(s)

    if "war_losses" in ex:
        series("General Staff losses", official.war_losses)
    if "nbu_fx" in ex:
        for cur in ("USD", "EUR"):
            series(f"NBU {cur}", official.nbu_fx, cur)
    if "nbu_rate" in ex:
        series("NBU key rate", official.nbu_key_rate)
    if "nbp_fx" in ex:
        for cur in ("EUR", "USD", "UAH"):
            series(f"NBP {cur}", official.nbp_fx, cur)
    if "eurostat_hicp" in ex:
        for geo in dict.fromkeys(["EU27_2020", *[g for g in plan.countries if g != "UA"]]):
            series(f"Eurostat HICP {geo}", official.eurostat_hicp, geo)
    if "fear_greed" in ex:
        series("Fear & Greed", crypto.fear_greed)
    if "defi_tvl" in ex:
        series("DeFi TVL", crypto.defi_tvl)
    if "stablecoins" in ex:
        series("Stablecoins", crypto.stablecoins)
    if "openalex" in ex:
        for topic in plan.research_topics:
            progress(f"OpenAlex: {topic}")
            trend = _try(c, "OpenAlex", science.openalex_trend, topic)
            if trend:
                c.research.append(trend)

    if "gdacs" in ex:
        progress("GDACS")
        c.events += _try(c, "GDACS", hazards.gdacs) or []
    if "earthquakes" in ex:
        progress("USGS")
        c.events += _try(c, "USGS", hazards.earthquakes) or []
    if "eonet" in ex:
        progress("NASA EONET")
        c.events += _try(c, "NASA EONET", hazards.eonet) or []
    if "space_weather" in ex:
        progress("NOAA SWPC")
        c.forecasts["kp"] = _try(c, "NOAA SWPC", hazards.kp_forecast) or []
    for loc in plan.locations:
        name = loc["name"]
        if "weather" in ex:
            progress(f"Open-Meteo: {name}")
            w = _try(c, "Open-Meteo", hazards.weather, loc["lat"], loc["lon"])
            if w:
                c.forecasts.setdefault("weather", {})[name] = w
        if "floods" in ex and loc.get("river"):
            progress(f"GloFAS: {loc['river']['name']}")
            f = _try(c, "GloFAS", hazards.river, loc["river"]["lat"], loc["river"]["lon"])
            if f:
                c.forecasts.setdefault("floods", {})[name] = (loc["river"]["name"], f)
        if "air_quality" in ex:
            a = _try(c, "CAMS air quality", hazards.air_quality, loc["lat"], loc["lon"])
            if a:
                c.forecasts.setdefault("air", {})[name] = a


def _hazard_block(c: Collected) -> Dict[str, Any]:
    if not (c.events or c.forecasts):
        return {}
    alerts = hz.event_alerts(c.events)
    for name, daily in c.forecasts.get("weather", {}).items():
        alerts += hz.weather_alerts(name, daily)
    for name, (river_name, daily) in c.forecasts.get("floods", {}).items():
        alerts += hz.flood_alerts(name, river_name, daily)
    for name, hourly in c.forecasts.get("air", {}).items():
        alerts += hz.air_alerts(name, hourly)
    alerts += hz.kp_alerts(c.forecasts.get("kp", []))
    return hz.summarize(alerts)


def _indicator_rows(series: List[Series]) -> List[Dict[str, Any]]:
    out = []
    for s in series:
        v = s.values
        base = v[-31] if len(v) > 30 else v[0]
        row = {"series": s.name, "kind": s.kind, "unit": s.unit, "source": s.source,
               **timeseries.summarize_series(s.dates, v),
               "change_30": round(v[-1] / base - 1, 4) if base else None}
        if s.kind == "war_losses":
            row["intensity"] = timeseries.regime_chain(v, 30)
        out.append(row)
    return out


def _macro_block(series: List[Series]) -> List[Dict[str, Any]]:
    out = []
    for s in series:
        v = s.values
        fc = timeseries.holt_forecast(v[-15:], steps=2)
        out.append({
            "series": s.name, "unit": s.unit, "last_year": s.dates[-1], "latest": round(v[-1], 2),
            "avg_5y": round(sum(v[-5:]) / len(v[-5:]), 2),
            "trend_10y": round(timeseries.linear_trend(v[-10:])["slope"], 3),
            "forecast_next": fc["forecast"], "band_80": fc["band"],
        })
    return out


def analyze(plan: Plan, c: Collected, use_llm: bool = True,
            record_forecasts: bool = True) -> Dict[str, Any]:
    staticity = STATICITY.get(plan.domain, "operational")
    tiers = profiles.trust_tiers()
    for a in c.articles:  # news found by search inherits the trust from sources.json
        if not a.tier:
            a.tier = tiers.get(a.source.lower(), 0)
    passport = signals.score_articles(c.articles, plan.keywords, staticity)
    relevant = [a for a in c.articles if a.passport["R"] > 0] or c.articles
    methods = signals.method_indices(relevant)

    by_kind: Dict[str, List[Series]] = {}
    for s in c.series:
        by_kind.setdefault(s.kind, []).append(s)

    market_rows, closes = [], {}
    for s in by_kind.get("price", []):
        row = market.analyze_prices(s.name, s.dates, s.values, plan.horizon_days,
                                    crypto=s.name in markets.CRYPTO)
        row["source"], row["currency"] = s.source, s.unit
        market_rows.append(row)
        closes[s.name] = dict(zip(s.dates, s.values))
    correlation = market.correlation_matrix(closes) if len(closes) > 1 else {}
    returns_30d = {r["asset"]: r["change_30d"] for r in market_rows if "change_30d" in r}

    attention = []
    for s in by_kind.get("news_volume", []) + by_kind.get("attention", []) + \
            by_kind.get("news_tone", []):
        attention.append({"series": s.name, "kind": s.kind, "unit": s.unit,
                          **timeseries.summarize_series(s.dates, s.values)})
    volume = next((a for a in attention if a["kind"] == "news_volume"), None)
    tone = next((a for a in attention if a["kind"] == "news_tone"), None)
    # preferred source of the crisis chain: news coverage, then combat intensity, then attention
    chain_src = (by_kind.get("news_volume") or by_kind.get("war_losses")
                 or by_kind.get("attention") or [None])[0]
    crisis = timeseries.regime_chain(chain_src.values, plan.horizon_days) if chain_src else {}
    if crisis:
        crisis["series"] = chain_src.name
    shown = {"price", "macro", "news_volume", "news_tone", "attention"}
    indicators = _indicator_rows([s for s in c.series if s.kind not in shown])

    result: Dict[str, Any] = {
        "plan": plan.to_dict(),
        "generated": time.time(),
        "sources_used": c.sources_used,
        "errors": c.errors,
        "counts": {"articles": len(c.articles), "series": len(c.series)},
        "stories": passport["stories"][:15],
        "n_stories": passport["n_stories"],
        "methods": methods,
        "jervis": signals.jervis_divergence(methods.get("weighted_sentiment", 0), returns_30d),
        "markets": market_rows,
        "correlation": correlation,
        "macro": _macro_block(by_kind.get("macro", [])),
        "attention": attention,
        "indicators": indicators,
        "crisis_chain": crisis,
        "hazards": _hazard_block(c),
        "research": c.research,
        "pages": c.pages,
        "articles": [a.to_dict() for a in c.articles],
        "hypothesis": None,
        "forecast_ids": [],
        "summary": "",
    }

    if plan.hypothesis:
        result["hypothesis"] = {"text": plan.hypothesis, "polarity": plan.polarity,
                                **logic.evaluate(plan.prior, plan.polarity, methods, volume,
                                                 tone, crisis, returns_30d,
                                                 plan.asset_direction)}

    if record_forecasts:
        for row in market_rows:
            if "monte_carlo" in row:
                fid = journal.record("market_up", f"{row['asset']} higher in "
                                     f"{plan.horizon_days}d than {row['last']}",
                                     row["monte_carlo"]["p_up"], plan.horizon_days,
                                     asset=row["asset"], start_price=row["last"],
                                     query_id=plan.query_id)
                result["forecast_ids"].append(fid)
        if result["hypothesis"]:
            fid = journal.record("hypothesis", plan.hypothesis, result["hypothesis"]["posterior"],
                                 plan.horizon_days, query_id=plan.query_id)
            result["forecast_ids"].append(fid)

    if use_llm:
        write_summary(plan, result)
    return result


def write_summary(plan: Plan, result: Dict[str, Any]) -> None:
    """LLM assessment of the computed results (numbers never come from the model)."""
    if not llm.enabled():
        return
    facts = json.dumps({k: result[k] for k in ("methods", "jervis", "crisis_chain",
                                               "hypothesis", "macro")},
                       ensure_ascii=False, default=str)[:6000]
    facts += "\nTop stories:\n" + "\n".join(
        f"- {s['title']} (sources {s['sources']}, T={s['truth']})" for s in result["stories"][:8])
    facts += "\nMarkets:\n" + "\n".join(
        f"- {m['asset']}: last {m.get('last')} {m.get('currency', '')}, "
        f"30d change {m.get('change_30d', 0) * 100:+.1f}%, trend {m.get('trend')}, "
        f"P(higher in {plan.horizon_days}d) {m.get('monte_carlo', {}).get('p_up', 0) * 100:.0f}%"
        for m in result["markets"] if "error" not in m)
    if result["indicators"]:
        facts += "\nIndicators:\n" + "\n".join(
            f"- {i['series']}: last {i.get('last')} {i['unit']}, 30d change "
            f"{(i.get('change_30') or 0) * 100:+.1f}%, z {i.get('z_last')}" for i in result["indicators"])
    hzd = result["hazards"]
    if hzd:
        facts += f"\nHazard alerts {hzd['by_level']}:\n" + "\n".join(
            f"- {a['level']} {a['hazard']} {a['location']} {a['date']}: {a['value']}"
            for a in hzd["alerts"][:15])
    if result["research"]:
        facts += "\nResearch trends:\n" + "\n".join(
            f"- {r['topic']}: {r['last_full_year']} works, growth {r['growth']}"
            for r in result["research"])
    rd = result.get("reading") or {}
    if rd.get("claims"):
        facts += "\nStatements from full articles:\n" + "\n".join(
            f"- [{c['source']}] {c['text']}" for c in rd["claims"][:20])
    if rd.get("conflicts"):
        facts += "\nContradictions between outlets:\n" + "\n".join(
            f"- {c['point']}: " + " / ".join(c["versions"]) for c in rd["conflicts"])
    try:
        result["summary"] = llm.summarize(plan.topic, LANG_NAMES.get(plan.lang, "English"), facts)
    except (FetchError, ValueError) as exc:
        result["errors"].append(f"LLM: {str(exc)[:160]}")


def finish(plan: Plan, c: Collected, use_llm: bool = True, record_forecasts: bool = True,
           read_full: bool = True, progress: Progress = lambda s: None) -> Dict[str, Any]:
    """Analysis, then full texts of the top stories, then the written assessment."""
    result = analyze(plan, c, use_llm=False, record_forecasts=record_forecasts)
    if read_full:
        result["reading"] = reading.read_stories(result["stories"], plan.lang, use_llm, progress)
        if result["reading"]["note"]:
            result["errors"].append(result["reading"]["note"])
    if use_llm:
        write_summary(plan, result)
    return result
