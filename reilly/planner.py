"""Block 1 — task: validate the topic, classify the domain, detect assets,
countries and URLs, and build the multilingual collection plan."""

import hashlib
import re
import time
from typing import List, Optional

from . import llm
from .analytics import text as tx
from .collectors.markets import ALIASES
from .http import FetchError
from .models import Plan

DOMAINS = {
    "ECONOMY_MARKETS": ["price", "market", "stock", "share", "inflation", "gdp", "econom", "bank",
                        "crypto", "bitcoin", "rate", "ціна", "ринок", "акці", "інфляц", "економ",
                        "крипт", "біткоїн", "курс", "preis", "markt", "aktie", "wirtschaft",
                        "prix", "marché", "économ", "precio", "mercado", "econom", "prezzo",
                        "mercato", "cena", "rynek", "gospodar", "inflac"],
    "SUPPLY_CHAIN_INDUSTRY": ["supply", "logist", "factory", "plant", "production", "manufactur",
                              "port", "rail", "постача", "логіст", "завод", "виробн", "лізни",
                              "liefer", "fabrik", "produktion", "usine", "approvision",
                              "fábrica", "suministro", "fabbrica", "fornitur", "fabryk",
                              "dostaw", "produkc"],
    "ENERGY": ["energy", "oil", "gas", "electric", "power grid", "енерг", "нафт", "газ",
               "електр", "energie", "strom", "énergie", "pétrole", "energía", "petróleo",
               "energia", "petrolio", "ropa"],
    "SECURITY_GEOPOLITICS": ["war", "military", "defen", "sanction", "conflict", "nato", "army",
                             "війн", "оборон", "санкці", "конфлікт", "армі", "krieg", "militär",
                             "guerre", "militaire", "guerra", "militar", "wojn", "wojsk"],
    "SOCIETY_POLITICS": ["election", "protest", "poll", "government", "vote", "вибор", "протест",
                         "уряд", "wahl", "regierung", "élection", "gouvernement", "elección",
                         "gobierno", "elezion", "governo", "wybor", "rząd"],
    "SCIENCE_TECH": ["ai ", "chip", "semiconductor", "research", "technolog", "space", "drone",
                     "штучн", "чіп", "технолог", "дрон", "halbleiter", "technologie",
                     "tecnolog", "półprzewod"],
}
# Data staticity class per domain (decay speed of news value)
STATICITY = {"ECONOMY_MARKETS": "operational", "SECURITY_GEOPOLITICS": "operational",
             "ENERGY": "operational", "SUPPLY_CHAIN_INDUSTRY": "trend",
             "SOCIETY_POLITICS": "operational", "SCIENCE_TECH": "trend", "GENERAL": "operational"}

COUNTRIES = {
    "UA": ["ukrain", "україн", "ukrain", "ucrain", "ukrai"],
    "DE": ["german", "німеч", "deutschland", "allemagne", "alemania", "germania", "niemc", "niemiec"],
    "FR": ["france", "french", "франц", "frankreich", "francia", "francj"],
    "PL": ["poland", "polish", "польщ", "polen", "pologne", "polonia", "polsk"],
    "IT": ["italy", "italian", "італ", "italien", "italie", "italia", "włoch"],
    "ES": ["spain", "spanish", "іспан", "spanien", "espagne", "españa", "hiszpan"],
    "GB": ["united kingdom", "britain", "british", "британ", "großbritannien"],
    "US": ["united states", "usa", " us ", "american", "сша", "америк", "vereinigte staaten"],
    "CN": ["china", "chinese", "китай", "chine", "chiny", "cina"],
    "RU": ["russia", "russian", "росі", "russland", "russie", "rusia", "rosj"],
    "TR": ["turkey", "türkiye", "туреч", "türkei", "turquie", "turcja"],
    "NL": ["netherlands", "dutch", "нідерланд", "niederlande", "pays-bas", "holandi"],
    "RO": ["romania", "румун", "rumänien", "roumanie", "rumuni"],
    "CZ": ["czech", "чех", "tschechien", "tchéquie", "czech"],
    "JP": ["japan", "япон", "japon", "giappone", "japoni"],
    "IN": ["india", "індія", "indien", "inde", "indie"],
}
INJECTION = ["ignore previous instructions", "ignore all previous", "forget everything",
             "system prompt", "ігноруй попередні", "забудь усе"]
URL = re.compile(r"https?://[^\s,;]+")


class Rejected(ValueError):
    pass


def _contains(low: str, words: List[str], stem: str) -> bool:
    if " " in stem:
        return stem in f" {low} "
    return any(w.startswith(stem) for w in words)


def classify(topic: str) -> str:
    low, words = topic.lower(), tx.tokens(topic)
    scores = {d: sum(_contains(low, words, s) for s in stems) for d, stems in DOMAINS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "GENERAL"


def detect_assets(topic: str) -> List[str]:
    low, words = topic.lower(), tx.tokens(topic)
    found = []
    for name, symbol in ALIASES.items():
        hit = (f" {name} " in f" {low} ") if (" " in name or "/" in name or "&" in name) \
            else name in words
        if hit and symbol not in found:
            found.append(symbol)
    found += [m for m in re.findall(r"\$([A-Z][A-Z0-9.\-=^]{0,9})", topic) if m not in found]
    return found


def detect_countries(topic: str) -> List[str]:
    low, words = f" {topic.lower()} ", tx.tokens(topic)
    return [iso for iso, stems in COUNTRIES.items() if any(_contains(low, words, s) for s in stems)]


def build(topic: str, lang: str = "en", assets: Optional[List[str]] = None,
          countries: Optional[List[str]] = None, urls: Optional[List[str]] = None,
          search_langs: Optional[List[str]] = None, hypothesis: str = "",
          polarity: str = "risk", asset_direction: str = "auto", prior: float = 0.5,
          horizon_days: int = 30, translate: bool = True) -> Plan:
    topic = (topic or "").strip()
    if len(topic) < 5:
        raise Rejected("too_short")
    if any(m in topic.lower() for m in INJECTION):
        raise Rejected("injection")

    found_urls = [u.rstrip(".)\"'") for u in URL.findall(topic)]
    clean = URL.sub(" ", topic).strip()
    langs = search_langs or list(dict.fromkeys([lang, "en"]))
    # short keyword queries match news search better than a full sentence
    base = " ".join(tx.keywords(clean, 4)) or clean
    queries = {lng: base for lng in langs}
    if translate and llm.enabled():
        try:
            queries.update(llm.translate_query(clean, langs))
        except (FetchError, ValueError, KeyError):
            pass  # keep the keyword query for every language

    qid = "REQ_" + hashlib.sha1(f"{topic}{time.time()}".encode()).hexdigest()[:10].upper()
    return Plan(
        query_id=qid, topic=clean, lang=lang, domain=classify(clean),
        keywords=tx.keywords(" ".join([clean, *queries.values()]), 16),
        search_langs=langs, search_queries=queries,
        assets=[a.strip() for a in (assets or detect_assets(clean)) if a.strip()],
        countries=[c.strip().upper() for c in (countries or detect_countries(clean)) if c.strip()],
        urls=(urls or []) + found_urls, hypothesis=hypothesis.strip(),
        polarity="positive" if polarity.startswith("p") else "risk",
        asset_direction=asset_direction if asset_direction in ("up", "down") else "auto",
        prior=min(max(prior, 0.01), 0.99), horizon_days=horizon_days,
    )
