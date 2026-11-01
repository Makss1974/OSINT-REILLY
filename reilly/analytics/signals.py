"""Signal passport (REILLY 5-factor matrix) and story clustering.

For every article:
  R  relevance   [0..1]   share of topic keywords present (stem match)
  A  recency     [0..1]   A = 1 / (1 + days_ago * S), S = data staticity class
  V  importance  [0.1..1] source tier + how many independent outlets carry the story
  Snt sentiment  [-1..1]  GDELT tone if available, else multilingual lexicon
  T  truth       {-2,-1,+1,+2} corroboration by independent domains minus hedging
                 (no zero by design: every signal is either leaning true or false)
  weight = R * A * V * (T + 2) / 4
"""

import time
from collections import defaultdict
from typing import Any, Dict, List, Sequence
from urllib.parse import urlparse

from ..models import Article
from . import text as tx

# S coefficients (per day) from the REILLY signal evaluation matrix
STATICITY = {"static": 0.0, "trend": 0.02, "operational": 0.1, "flash": 0.5}

# Wire services and outlets with formal corrections policy -> tier 1
TIER1 = {
    "reuters", "apnews", "afp", "bloomberg", "ft.com", "wsj", "economist", "bbc", "dw.com",
    "lemonde", "elpais", "corriere", "spiegel", "faz.net", "handelsblatt", "nytimes",
    "theguardian", "politico", "ukrinform", "suspilne", "pravda.com.ua", "epravda",
    "rzeczpospolita", "pap.pl", "ansa", "efe", "euronews", "lesechos", "ilsole24ore",
    "kyivindependent", "interfax", "nikkei", "cnbc", "france24", "rai", "tagesschau",
}


def source_key(article: Article) -> str:
    host = urlparse(article.url).netloc.lower().removeprefix("www.")
    if article.collector == "google_news_rss" or not host or "news.google" in host:
        return (article.source or host).lower()
    return host


def is_tier1(name: str) -> bool:
    name = name.lower().replace(" ", "")
    return any(t.replace(" ", "") in name for t in TIER1)


def relevance_score(keywords: List[str], body: str) -> float:
    """Short topic -> share of its words present; long profile vocabularies ->
    saturating count of hits (3 distinct hits = fully relevant)."""
    if len(keywords) <= 12:
        return tx.stem_overlap(keywords, body)
    return min(1.0, tx.distinct_hits(body, keywords) / 3)


def cluster(articles: Sequence[Article], threshold: float = 0.34) -> List[List[int]]:
    """Greedy single-pass clustering of near-duplicate headlines."""
    clusters: List[List[int]] = []
    heads: List[str] = []
    for i, a in enumerate(articles):
        for c, head in enumerate(heads):
            if tx.jaccard(a.title, head) >= threshold:
                clusters[c].append(i)
                break
        else:
            clusters.append([i])
            heads.append(a.title)
    return clusters


def score_articles(articles: List[Article], keywords: List[str],
                   staticity: str = "operational", now: float = 0.0) -> Dict[str, Any]:
    now = now or time.time()
    s_coef = STATICITY.get(staticity, 0.1)
    groups = cluster(articles)
    story_of = {}
    story_sources = {}
    for g_id, members in enumerate(groups):
        srcs = {source_key(articles[i]) for i in members}
        story_sources[g_id] = srcs
        for i in members:
            story_of[i] = g_id

    for i, a in enumerate(articles):
        body = f"{a.title} {a.snippet}"
        lex = tx.lexicon_counts(body)
        days = max(0.0, (now - a.published) / 86400) if a.published else 7.0
        n_src = len(story_sources[story_of[i]])
        tier1 = a.tier == 1 or (a.tier == 0 and is_tier1(source_key(a)))
        relevance = relevance_score(keywords, body)
        recency = 1.0 / (1.0 + days * s_coef)
        trust_bonus = 0.3 if tier1 else 0.1 if a.tier == 2 else -0.1 if a.tier == 3 else 0.0
        importance = max(0.1, min(1.0, 0.2 + trust_bonus + 0.1 * (n_src - 1)))
        sent = (max(-10.0, min(10.0, a.tone)) / 10.0) if a.tone is not None else tx.sentiment(body)
        if n_src >= 3 and not lex["hedge"]:
            truth = 2
        elif n_src >= 2 or (tier1 and not lex["hedge"]):
            truth = 1
        elif lex["hedge"]:
            truth = -2
        else:
            truth = -1
        a.passport = {
            "R": round(relevance, 2), "A": round(recency, 2), "V": round(importance, 2),
            "Snt": round(sent, 2), "T": truth, "sources_in_story": n_src,
            "weight": round(relevance * recency * importance * (truth + 2) / 4, 4),
            "lex": {k: v for k, v in lex.items() if v},
        }

    stories = []
    for g_id, members in enumerate(groups):
        best = max(members, key=lambda i: articles[i].passport["weight"])
        # one link per outlet, strongest first: lets the reader compare versions of a story
        ranked = sorted(members, key=lambda i: -articles[i].passport["weight"])
        outlets, seen = [], set()
        for i in ranked:
            key = source_key(articles[i])
            if key not in seen:
                seen.add(key)
                outlets.append({"source": articles[i].source or key, "url": articles[i].url})
        stories.append({
            "members": outlets[:6],
            "title": articles[best].title,
            "url": articles[best].url,
            "sources": len(story_sources[g_id]),
            "articles": len(members),
            "weight": round(sum(articles[i].passport["weight"] for i in members), 4),
            "truth": articles[best].passport["T"],
            "sentiment": round(sum(articles[i].passport["Snt"] for i in members) / len(members), 2),
        })
    stories.sort(key=lambda s: s["weight"], reverse=True)
    return {"stories": stories, "n_articles": len(articles), "n_stories": len(groups)}


def method_indices(articles: List[Article]) -> Dict[str, Any]:
    """Aggregate REILLY methods over weighted articles."""
    if not articles:
        return {}
    tot_w = sum(a.passport.get("weight", 0) for a in articles) or 1.0
    agg = defaultdict(float)
    hits = defaultdict(int)
    for a in articles:
        w = a.passport.get("weight", 0)
        for cat, n in a.passport.get("lex", {}).items():
            agg[cat] += w * min(n, 3) / 3
            hits[cat] += 1
    n = len(articles)
    idx = {cat: round(agg[cat] / tot_w, 3) for cat in tx.LEXICON}
    sentiment = sum(a.passport.get("Snt", 0) * a.passport.get("weight", 0) for a in articles) / tot_w
    finance, weak = idx["finance_in"], idx["physical_weak"]
    return {
        "weighted_sentiment": round(sentiment, 3),
        "goldratt_constraint_index": idx["constraint"],
        "constraint_share": round(hits["constraint"] / n, 3),
        "linguistic_stress_index": idx["stress"],
        "hedging_share": round(hits["hedge"] / n, 3),
        # money announced while physical activity is reported weak
        "capital_inversion_index": round(min(finance, weak) * 2, 3),
        "capital_inversion_flag": finance > 0.05 and weak > 0.05,
        "verified_share": round(sum(1 for a in articles if a.passport.get("T", 0) > 0) / n, 3),
    }


def jervis_divergence(news_sentiment: float, market_returns: Dict[str, float]) -> Dict[str, Any]:
    """Jervis: cheap signals (words) vs costly signals (money at risk).
    Flags an 'inverted mirror' when talk and prices point in opposite directions."""
    if not market_returns:
        return {}
    avg = sum(market_returns.values()) / len(market_returns)
    talk = "POSITIVE" if news_sentiment > 0.1 else "NEGATIVE" if news_sentiment < -0.1 else "NEUTRAL"
    money = "UP" if avg > 0.02 else "DOWN" if avg < -0.02 else "FLAT"
    inverted = (talk == "POSITIVE" and money == "DOWN") or (talk == "NEGATIVE" and money == "UP")
    return {"cheap_signal": talk, "costly_signal": money, "avg_30d_return": round(avg, 4),
            "inverted_mirror": inverted}
