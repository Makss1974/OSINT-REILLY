"""Blocks 2-4: collect open data for a plan and run the analytics."""

import json
import logging
import time
from typing import Any, Callable, Dict, List

from . import journal, llm
from .analytics import logic, market, signals, timeseries
from .collectors import brightdata, macro, markets, news, pages, wiki
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


def collect(plan: Plan, progress: Progress = lambda s: None) -> Collected:
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

    seen, unique = set(), []
    for a in articles:
        key = a.url or a.title.lower()
        if a.title and key not in seen:
            seen.add(key)
            unique.append(a)
    c.articles = unique

    en_q = plan.search_queries.get("en", plan.topic)
    progress("GDELT timelines")
    timelines = _try(c, "GDELT", news.gdelt_timelines, en_q, "", 90)
    if timelines:
        c.series += [s for s in timelines if s.values]

    for lang in dict.fromkeys([plan.lang, "en"]):
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
    return c


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
    chain_src = (by_kind.get("news_volume") or by_kind.get("attention") or [None])[0]
    crisis = timeseries.regime_chain(chain_src.values, plan.horizon_days) if chain_src else {}

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
        "crisis_chain": crisis,
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

    if use_llm and llm.enabled():
        facts = json.dumps({k: result[k] for k in ("methods", "jervis", "crisis_chain",
                                                   "hypothesis", "macro")},
                           ensure_ascii=False, default=str)[:6000]
        facts += "\nTop stories:\n" + "\n".join(
            f"- {s['title']} (sources {s['sources']}, T={s['truth']})" for s in result["stories"][:8])
        facts += "\nMarkets:\n" + "\n".join(
            f"- {m['asset']}: last {m.get('last')} {m.get('currency', '')}, "
            f"30d change {m.get('change_30d', 0) * 100:+.1f}%, trend {m.get('trend')}, "
            f"P(higher in {plan.horizon_days}d) {m.get('monte_carlo', {}).get('p_up', 0) * 100:.0f}%"
            for m in market_rows if "error" not in m)
        try:
            result["summary"] = llm.summarize(plan.topic, LANG_NAMES.get(plan.lang, "English"), facts)
        except (FetchError, ValueError) as exc:
            result["errors"].append(f"LLM: {str(exc)[:160]}")
    return result
