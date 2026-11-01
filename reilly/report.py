"""Block 5 — report. One table model feeds the console, Markdown and HTML."""

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from . import config
from .i18n import Translator


def pct(x: Any, digits: int = 1) -> str:
    return "—" if x is None else f"{x * 100:+.{digits}f}%"


def num(x: Any, digits: int = 2) -> str:
    if x is None:
        return "—"
    if isinstance(x, float) and abs(x) >= 1000:
        return f"{x:,.0f}".replace(",", " ")
    return f"{x:.{digits}f}" if isinstance(x, float) else str(x)


def sections(r: Dict[str, Any], t: Translator, full: bool = False) -> List[Dict[str, Any]]:
    """Report as a list of tables. full=True gives longer lists (window UI)."""
    out: List[Dict[str, Any]] = []
    p = r["plan"]
    out.append({"key": "plan", "title": t("plan"), "columns": ["", ""], "rows": [
        [t("topic_prompt"), p["topic"]],
        [t("domain"), t("p_" + p["profile"]) if p.get("profile") else p["domain"]],
        [t("queries"), "; ".join(f"{k}: {v}" for k, v in p["search_queries"].items())],
        [t("assets_prompt").split(" (")[0], ", ".join(p["assets"]) or "—"],
        [t("countries_prompt").split(" (")[0], ", ".join(p["countries"]) or "—"],
        [t("sources"), ", ".join(r["sources_used"]) or "—"],
        [t("errors"), "; ".join(r["errors"]) or "—"],
    ]})

    shown = r["stories"][:40 if full else 12]
    out.append({"key": "stories",
                "title": f"{t('stories')} — {r['counts']['articles']} / {r['n_stories']}",
                "columns": [t("story"), t("n_sources"), t("truth"), t("sentiment"), t("weight")],
                "rows": [[s["title"][:110], s["sources"], f"{s['truth']:+d}",
                          num(s["sentiment"]), num(s["weight"], 3)] for s in shown],
                "links": [s["url"] for s in shown]})

    m = r["methods"]
    if m:
        rows = [[t("m_sentiment"), num(m["weighted_sentiment"], 3)],
                [t("m_goldratt"), f"{num(m['goldratt_constraint_index'], 3)} "
                                  f"({pct(m['constraint_share'], 0)})"],
                [t("m_stress"), num(m["linguistic_stress_index"], 3)],
                [t("m_inversion"), num(m["capital_inversion_index"], 3) +
                 (" ⚠" if m["capital_inversion_flag"] else "")],
                [t("m_verified"), pct(m["verified_share"], 0)],
                [t("m_hedging"), pct(m["hedging_share"], 0)]]
        j = r.get("jervis") or {}
        if j:
            rows.append([t("m_jervis"), f"{j['cheap_signal']} / {j['costly_signal']}" +
                         (" ⚠ inverted mirror" if j["inverted_mirror"] else "")])
        c = r.get("crisis_chain") or {}
        if c:
            rows.append([t("crisis_chain"), f"{c['current_state']} → "
                                            f"{c['p_crisis_day_in_horizon'] * 100:.0f}% "
                                            f"(base {c['p_crisis_base'] * 100:.0f}%)"])
        out.append({"key": "methods", "title": t("methods"), "columns": [t("method"), t("value")], "rows": rows})

    if r["markets"]:
        rows = []
        for a in r["markets"]:
            if "error" in a:
                rows.append([a["asset"], a["error"]] + [""] * 8)
                continue
            mc, mk = a["monte_carlo"], a["markov"]
            rows.append([
                f"{a['asset']} ({a['source']})", num(a["last"]), pct(a["change_30d"]),
                pct(a["change_1y"]), pct(a["ann_volatility"], 0), pct(a["max_drawdown"], 0),
                f"{a['rsi14']:.0f}", f"{a['trend']} H={a['hurst']:.2f}",
                f"{mc['p_up'] * 100:.0f}%",
                f"{num(mc['quantiles']['p05'])} … {num(mc['quantiles']['p95'])}",
                f"{mk['current_state']}",
            ])
        out.append({"key": "markets", "title": f"{t('markets')} — {t('horizon_prompt')} {p['horizon_days']}",
                    "columns": [t("asset"), t("last"), t("chg30"), t("chg1y"), t("vol"), t("mdd"),
                                "RSI", t("trend"), t("p_up"), t("range90"), t("regime")],
                    "rows": rows})
    if r["correlation"]:
        names = list(r["correlation"])
        out.append({"key": "correlation", "title": t("correlation"), "columns": [""] + names,
                    "rows": [[a] + [num(r["correlation"][a][b]) for b in names] for a in names]})

    if r["macro"]:
        out.append({"key": "macro", "title": t("macro"),
                    "columns": [t("indicator"), t("latest"), t("avg5"), t("trend"), t("forecast")],
                    "rows": [[f"{x['series']} ({x['unit']})", f"{x['latest']} ({x['last_year']})",
                              x["avg_5y"], f"{x['trend_10y']:+.2f}/yr",
                              " → ".join(f"{v:.1f}" for v in x["forecast_next"])]
                             for x in r["macro"]]})

    if r["attention"]:
        out.append({"key": "attention", "title": t("attention"),
                    "columns": [t("series"), t("last"), t("recent_vs_base"), "z", t("anomalies")],
                    "rows": [[a["series"], num(a.get("last")), pct(a.get("recent_vs_base"), 0),
                              num(a.get("z_last")),
                              ", ".join(f"{x['date']}({x['z']:+.0f})" for x in a.get("anomalies", [])[-4:])
                              or "—"] for a in r["attention"]]})

    if r.get("indicators"):
        rows = []
        for i in r["indicators"]:
            extra = ""
            if i.get("intensity"):
                extra = (f"{i['intensity']['current_state']} → "
                         f"{i['intensity']['p_crisis_day_in_horizon'] * 100:.0f}%")
            rows.append([f"{i['series']} ({i['unit']})", num(i.get("last")),
                         pct(i.get("change_30")), pct(i.get("recent_vs_base"), 0),
                         num(i.get("z_last")), extra or "—",
                         ", ".join(f"{x['date']}({x['z']:+.0f})" for x in i.get("anomalies", [])[-3:])
                         or "—"])
        out.append({"key": "indicators", "title": t("indicators"),
                    "columns": [t("series"), t("last"), t("chg30"), t("recent_vs_base"), "z",
                                t("intensity"), t("anomalies")], "rows": rows})

    hz = r.get("hazards") or {}
    if hz:
        alerts = hz["alerts"][:80 if full else 25]
        counts = ", ".join(f"{t('lvl_' + k)}: {v}" for k, v in hz["by_level"].items()) or "0"
        out.append({"key": "hazards", "title": f"{t('hazards')} — {counts}",
                    "columns": [t("level"), t("hazard"), t("location"), t("date"), t("value"),
                                t("source")],
                    "rows": [[t("lvl_" + a["level"]), t("hz_" + a["hazard"]), a["location"],
                              a["date"], a["value"], a["source"]] for a in alerts],
                    "links": [a.get("url", "") for a in alerts]})

    if r.get("research"):
        out.append({"key": "research", "title": t("research"),
                    "columns": [t("topic_prompt"), t("works_year"), t("growth"), t("by_year")],
                    "rows": [[x["topic"], x["last_full_year"], pct(x["growth"], 0),
                              "  ".join(f"{y}:{n}" for y, n in x["by_year"].items())]
                             for x in r["research"]]})

    h = r.get("hypothesis")
    if h:
        rows = [[e["evidence"], str(e["value"]), f"{e['llr']:+.3f}"] for e in h["evidence"]]
        rows.append([f"{t('prior')} → {t('posterior')}", f"{h['prior'] * 100:.0f}% → "
                     f"{h['posterior'] * 100:.0f}%", f"Σ {h['total_llr']:+.3f}"])
        out.append({"key": "hypothesis", "title": f"{t('hypothesis')}: {h['text']} [{h['polarity']}]",
                    "columns": [t("evidence"), t("value"), "LLR"], "rows": rows})

    if r["pages"]:
        out.append({"key": "pages", "title": t("pages"), "columns": ["URL", t("status"), "+", "−"],
                    "rows": [[pg["url"], pg["status"], len(pg.get("added", [])),
                              len(pg.get("removed", []))] for pg in r["pages"]]})
    return out


def to_markdown(r: Dict[str, Any], t: Translator) -> str:
    def cell(x: Any) -> str:
        return str(x).replace("|", "/").replace("\n", " ")

    lines = [f"# {t('title')}", "", f"`{r['plan']['query_id']}` · "
             f"{datetime.fromtimestamp(r['generated']):%Y-%m-%d %H:%M}", ""]
    for s in sections(r, t):
        lines += [f"## {s['title']}", "", "| " + " | ".join(cell(c) for c in s["columns"]) + " |",
                  "|" + "---|" * len(s["columns"])]
        lines += ["| " + " | ".join(cell(x) for x in row) + " |" for row in s["rows"]]
        lines.append("")
    if r["summary"]:
        lines += [f"## {t('summary')}", "", r["summary"], ""]
    lines += ["### Links", ""] + [f"- [{s['title'][:100]}]({s['url']})" for s in r["stories"][:15]]
    lines += ["", f"_{t('disclaimer')}_", ""]
    return "\n".join(lines)


def to_html(r: Dict[str, Any], t: Translator) -> str:
    e = html.escape
    parts = [f"<!doctype html><html lang='{r['plan']['lang']}'><head><meta charset='utf-8'>"
             f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>REILLY {e(r['plan']['query_id'])}</title><style>"
             "body{font:14px/1.45 system-ui,sans-serif;max-width:1200px;margin:24px auto;"
             "padding:0 16px;color:#1c2330;background:#fff}h1{font-size:22px}"
             "h2{font-size:16px;margin-top:28px;border-bottom:1px solid #d7dce4}"
             "table{border-collapse:collapse;width:100%;overflow-x:auto;display:block}"
             "td,th{border:1px solid #e1e5eb;padding:4px 8px;text-align:left;vertical-align:top}"
             "th{background:#f3f5f8}.note{color:#5b6475;font-style:italic}"
             "@media(prefers-color-scheme:dark){body{background:#12161d;color:#dde3ec}"
             "th{background:#1d2330}td,th{border-color:#2b3242}h2{border-color:#2b3242}}"
             "</style></head><body>",
             f"<h1>{e(t('title'))}</h1><p><code>{e(r['plan']['query_id'])}</code></p>"]
    for s in sections(r, t):
        parts.append(f"<h2>{e(s['title'])}</h2><table><tr>" +
                     "".join(f"<th>{e(str(c))}</th>" for c in s["columns"]) + "</tr>")
        parts += ["<tr>" + "".join(f"<td>{e(str(x))}</td>" for x in row) + "</tr>"
                  for row in s["rows"]]
        parts.append("</table>")
    if r["summary"]:
        parts.append(f"<h2>{e(t('summary'))}</h2><p>{e(r['summary']).replace(chr(10), '<br>')}</p>")
    parts.append("<h2>Links</h2><ul>" + "".join(
        f"<li><a href='{e(s['url'])}' rel='noopener noreferrer'>{e(s['title'][:120])}</a></li>"
        for s in r["stories"][:15]) + "</ul>")
    parts.append(f"<p class='note'>{e(t('disclaimer'))}</p></body></html>")
    return "".join(parts)


def save(r: Dict[str, Any], t: Translator) -> Dict[str, Path]:
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = config.REPORTS_DIR / f"{datetime.fromtimestamp(r['generated']):%Y%m%d_%H%M}_" \
                                f"{r['plan']['query_id']}"
    paths = {"json": stem.with_suffix(".json"), "md": stem.with_suffix(".md"),
             "html": stem.with_suffix(".html")}
    paths["json"].write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str),
                             encoding="utf-8")
    paths["md"].write_text(to_markdown(r, t), encoding="utf-8")
    paths["html"].write_text(to_html(r, t), encoding="utf-8")
    return paths
