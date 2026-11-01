"""Macro-economic data: World Bank Open Data API (no key needed)."""

from typing import List

from ..http import get_json
from ..models import Series

INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": ("gdp_growth", "%"),
    "FP.CPI.TOTL.ZG": ("inflation", "%"),
    "SL.UEM.TOTL.ZS": ("unemployment", "%"),
    "BN.CAB.XOKA.GD.ZS": ("current_account", "% GDP"),
    "NE.EXP.GNFS.ZS": ("exports", "% GDP"),
}


def world_bank(country: str, indicator: str, years: int = 25) -> Series:
    data = get_json(
        f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}",
        params={"format": "json", "per_page": years, "mrv": years}, ttl=86400,
    )
    rows = data[1] if isinstance(data, list) and len(data) > 1 and data[1] else []
    points = sorted((r["date"], float(r["value"])) for r in rows if r.get("value") is not None)
    name, unit = INDICATORS.get(indicator, (indicator, ""))
    return Series(f"{country}:{name}", "macro", [p[0] for p in points],
                  [p[1] for p in points], unit, "world_bank")


def country_profile(country: str) -> List[Series]:
    return [world_bank(country, code) for code in INDICATORS]
