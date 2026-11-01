"""Multilingual text features (en, uk, de, fr, es, it, pl).

Lexicons are word stems matched at word start, so "shortage"/"shortages"
or "дефіцит"/"дефіциту" both hit. They feed the REILLY methods:
- sentiment (negative / positive vocabulary balance)
- Goldratt constraints: shortage / delay / capacity / energy / labour markers
- capital inversion: money flowing in vs. physical weakness
- linguistic stress: urgency and alarm vocabulary
- hedging: unverified-claim markers (lower truth score)
"""

import re
from typing import Dict, Iterable, List

WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

LEXICON: Dict[str, List[str]] = {
    "negative": [
        # en
        "crisis", "collapse", "crash", "decline", "fall", "drop", "loss", "risk", "war", "attack",
        "sanction", "default", "bankrupt", "recession", "fear", "plunge", "slump", "threat",
        "fail", "cut", "layoff", "protest", "strike", "fraud", "scandal", "warn",
        # uk
        "криз", "обвал", "падін", "спад", "втрат", "ризик", "війн", "атак", "санкці", "дефолт",
        "банкрут", "рецесі", "загроз", "скороч", "протест", "страйк", "шахрай", "скандал",
        # de
        "krise", "einbruch", "verlust", "risiko", "krieg", "angriff", "sanktion", "pleite",
        "insolvenz", "rezession", "drohung", "abbau", "streik", "betrug", "warnung",
        # fr
        "crise", "effondr", "chute", "baisse", "perte", "risque", "guerre", "attaque", "faillite",
        "récession", "menace", "grève", "fraude", "licenci",
        # es
        "crisis", "colapso", "caída", "pérdida", "riesgo", "guerra", "ataque", "quiebra",
        "recesión", "amenaza", "huelga", "despido",
        # it
        "crollo", "calo", "perdita", "rischio", "guerra", "attacco", "fallimento", "recessione",
        "minaccia", "sciopero", "licenzia",
        # pl
        "kryzys", "załaman", "spadek", "strat", "ryzyk", "wojn", "atak", "sankcj", "bankruct",
        "recesj", "zagroż", "strajk", "oszust", "zwolni",
    ],
    "positive": [
        "growth", "rise", "gain", "record", "boost", "recover", "surge", "rally", "profit",
        "agreement", "deal", "peace", "stable", "improv", "success", "invest", "expand",
        "зрост", "прибут", "рекорд", "відновл", "угод", "мир", "стабіль", "покращ", "успіх",
        "інвест", "розшир",
        "wachstum", "anstieg", "gewinn", "rekord", "erholung", "einigung", "frieden", "stabil",
        "croissance", "hausse", "bénéfice", "reprise", "accord", "paix",
        "crecimiento", "subida", "ganancia", "récord", "recuperación", "acuerdo", "paz",
        "crescita", "aumento", "guadagno", "ripresa", "accordo", "pace",
        "wzrost", "zysk", "rekord", "ożywien", "porozumien", "pokój", "stabiln",
    ],
    "constraint": [
        "shortage", "bottleneck", "delay", "backlog", "capacity", "outage", "blackout",
        "congestion", "rationing", "supply disruption", "disruption", "scarcity", "labor shortage",
        "дефіцит", "нестач", "затримк", "перебо", "вузьк", "потужніст", "блекаут", "відключ",
        "черг", "кадров",
        "engpass", "mangel", "lieferverzug", "verzögerung", "kapazität", "ausfall", "stau",
        "pénurie", "retard", "goulot", "capacité", "panne", "rupture",
        "escasez", "retraso", "cuello de botella", "capacidad", "apagón", "desabastec",
        "carenza", "ritardo", "strozzatura", "capacità", "blackout",
        "niedobór", "brak", "opóźnien", "wąskie gardło", "przepustow", "awari",
    ],
    "finance_in": [
        "tender", "contract", "procurement", "funding", "billion", "million", "budget",
        "investment", "subsid", "loan", "bond", "ipo",
        "тендер", "контракт", "закупів", "фінансув", "мільярд", "мільйон", "бюджет", "кредит",
        "ausschreibung", "auftrag", "milliard", "million", "förder", "haushalt",
        "appel d'offres", "contrat", "financement", "milliard", "subvention",
        "licitación", "contrato", "financiación", "millones", "subvención",
        "appalto", "contratto", "finanziament", "miliard", "milion",
        "przetarg", "umow", "finansowan", "miliard", "milion", "dotacj",
    ],
    "physical_weak": [
        "halt", "idle", "stopped", "closure", "shut", "stall", "standstill", "cancel", "abandon",
        "зупин", "простій", "закрит", "згорта", "заморож", "скасов",
        "stillstand", "stillgelegt", "schließung", "gestoppt", "abgesagt",
        "arrêt", "fermeture", "suspendu", "annul",
        "paraliz", "cierre", "detenid", "cancelad",
        "fermo", "chiusura", "sospes", "annullat",
        "wstrzyma", "zamknięc", "przestój", "odwoła",
    ],
    "stress": [
        "urgent", "emergency", "immediately", "panic", "alarm", "evacuat", "critical",
        "терміново", "надзвичайн", "негайно", "паніка", "тривог", "евакуац", "критичн",
        "dringend", "notfall", "sofort", "panik", "alarm", "evakuier", "kritisch",
        "urgent", "urgence", "immédiat", "panique", "évacu", "critique",
        "urgente", "emergencia", "inmediat", "pánico", "evacu", "crítico",
        "urgente", "emergenza", "immediat", "panico", "evacua", "critico",
        "pilne", "nagły", "natychmiast", "panik", "alarm", "ewakuac", "krytyczn",
    ],
    "hedge": [
        "reportedly", "allegedly", "rumor", "rumour", "unconfirmed", "sources say",
        "нібито", "чутки", "неперевірен", "за даними джерел",
        "angeblich", "gerücht", "unbestätigt", "soll ",
        "selon des sources", "rumeur", "non confirmé", "prétendu",
        "supuestamente", "rumor", "sin confirmar",
        "presunto", "presunta", "voci", "non confermat",
        "rzekomo", "plotk", "niepotwierdzon",
    ],
}

STOPWORDS = set("""
the a an and or of in on at to for with by from is are was were be about into over under
та і й в у на з із до за про що як це той ця від для по при чи
der die das und oder von im in auf zu für mit ist sind ein eine
le la les et ou de des du en au aux pour avec est sont un une
el la los las y o de del en para con es son un una
il lo la gli le e o di del in per con è sono un una
i w na z do za o że jak to od dla po przy czy
analyze analyse analysis проаналізуй аналіз стан state 2024 2025 2026
""".split())


def tokens(text: str) -> List[str]:
    return [w.lower() for w in WORD.findall(text or "")]


def keywords(text: str, limit: int = 8) -> List[str]:
    seen, out = set(), []
    for w in tokens(text):
        if len(w) > 3 and w not in STOPWORDS and w not in seen:
            seen.add(w)
            out.append(w)
    return out[:limit]


def _stem_hit(text_lower: str, words: List[str], stem: str) -> int:
    if " " in stem or "'" in stem:
        return text_lower.count(stem)
    if len(stem) >= 5:  # also inside compounds: Energiekrise, Lieferengpass
        return sum(1 for w in words if stem in w)
    return sum(1 for w in words if w.startswith(stem))


def lexicon_counts(text: str) -> Dict[str, int]:
    low = (text or "").lower()
    words = tokens(low)
    return {cat: sum(_stem_hit(low, words, s) for s in set(stems))
            for cat, stems in LEXICON.items()}


def sentiment(text: str) -> float:
    """Lexicon balance in [-1, 1]."""
    c = lexicon_counts(text)
    total = c["positive"] + c["negative"]
    return 0.0 if total == 0 else (c["positive"] - c["negative"]) / total


def stem_overlap(query_terms: Iterable[str], text: str, stem_len: int = 5) -> float:
    """Share of query terms present in the text (compared by first letters)."""
    terms = {t[:stem_len] for t in query_terms if len(t) > 2}
    if not terms:
        return 0.0
    stems = {w[:stem_len] for w in tokens(text)}
    return len(terms & stems) / len(terms)


def jaccard(a: str, b: str) -> float:
    sa = {w[:6] for w in tokens(a) if w not in STOPWORDS and len(w) > 2}
    sb = {w[:6] for w in tokens(b) if w not in STOPWORDS and len(w) > 2}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
