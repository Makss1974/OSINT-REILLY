"""Data contracts shared by all blocks."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Article:
    """One open-source text signal (news item, search result)."""
    title: str
    url: str
    source: str
    published: Optional[float]  # unix time
    lang: str
    collector: str
    snippet: str = ""
    tone: Optional[float] = None  # GDELT tone if known
    tier: int = 0  # source trust from sources.json: 1 trusted, 2 normal, 3 low, 0 unknown
    passport: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Series:
    """A dated numeric series (prices, pageviews, macro indicator...)."""
    name: str
    kind: str  # price | attention | macro | news_volume | news_tone
    dates: List[str]
    values: List[float]
    unit: str = ""
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Plan:
    """Block 1 output: what to collect for a topic."""
    query_id: str
    topic: str
    lang: str
    domain: str
    keywords: List[str]
    search_langs: List[str]
    search_queries: Dict[str, str]  # lang -> query text
    assets: List[str]
    countries: List[str]
    urls: List[str]
    hypothesis: str = ""
    polarity: str = "risk"  # risk | positive
    asset_direction: str = "auto"  # up | down | auto — asset move that supports it
    prior: float = 0.5
    horizon_days: int = 30
    profile: str = ""  # profile id from profiles.json, "" = free topic
    feeds: List[Dict[str, Any]] = field(default_factory=list)  # RSS feeds to read
    extras: List[str] = field(default_factory=list)  # special collectors
    filter_keywords: List[str] = field(default_factory=list)  # for general feeds
    locations: List[Dict[str, Any]] = field(default_factory=list)  # hazards
    research_topics: List[str] = field(default_factory=list)  # science

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Collected:
    articles: List[Article] = field(default_factory=list)
    series: List[Series] = field(default_factory=list)
    pages: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)  # disasters
    forecasts: Dict[str, Any] = field(default_factory=dict)  # weather / flood / air / kp
    research: List[Dict[str, Any]] = field(default_factory=list)  # papers, trends
    errors: List[str] = field(default_factory=list)
    sources_used: List[str] = field(default_factory=list)
