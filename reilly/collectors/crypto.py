"""Crypto market context: Fear & Greed index (alternative.me), DeFi total
value locked and stablecoin supply (DefiLlama). No keys required."""

from datetime import datetime, timezone

from ..http import get_json
from ..models import Series


def _day(ts) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y%m%d")


def fear_greed(days: int = 180) -> Series:
    rows = get_json("https://api.alternative.me/fng/", params={"limit": days}, ttl=10800)["data"]
    rows = sorted(rows, key=lambda r: int(r["timestamp"]))
    return Series("Crypto Fear & Greed", "sentiment_index", [_day(r["timestamp"]) for r in rows],
                  [float(r["value"]) for r in rows], "0-100", "alternative.me")


def defi_tvl(days: int = 365) -> Series:
    rows = get_json("https://api.llama.fi/v2/historicalChainTvl", ttl=21600)[-days:]
    return Series("DeFi TVL", "tvl", [_day(r["date"]) for r in rows],
                  [r["tvl"] / 1e9 for r in rows], "bn USD", "defillama")


def stablecoins(days: int = 365) -> Series:
    rows = get_json("https://stablecoins.llama.fi/stablecoincharts/all", ttl=21600)[-days:]
    return Series("Stablecoin supply", "tvl", [_day(r["date"]) for r in rows],
                  [r["totalCirculating"].get("peggedUSD", 0) / 1e9 for r in rows],
                  "bn USD", "defillama")
