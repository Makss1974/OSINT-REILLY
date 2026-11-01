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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Collected:
    articles: List[Article] = field(default_factory=list)
    series: List[Series] = field(default_factory=list)
    pages: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    sources_used: List[str] = field(default_factory=list)
