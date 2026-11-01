"""Market data: Yahoo Finance chart endpoint (stocks, indices, FX, futures)
and Binance / CoinGecko public APIs (crypto)."""

from datetime import datetime, timezone
from typing import Optional

from ..http import FetchError, get_json
from ..models import Series

# Human names -> symbols. Crypto symbols are routed to Binance first.
ALIASES = {
    "bitcoin": "BTC", "биткоин": "BTC", "біткоїн": "BTC", "btc": "BTC",
    "ethereum": "ETH", "ефір": "ETH", "eth": "ETH", "solana": "SOL", "xrp": "XRP",
    "gold": "GC=F", "золото": "GC=F", "gold price": "GC=F", "złoto": "GC=F",
    "brent": "BZ=F", "oil": "CL=F", "нафта": "BZ=F", "öl": "BZ=F", "pétrole": "BZ=F",
    "gas": "TTF=F", "газ": "TTF=F", "wheat": "ZW=F", "пшениця": "ZW=F",
    "copper": "HG=F", "мідь": "HG=F", "steel": "HRC=F", "сталь": "HRC=F",
    "s&p 500": "^GSPC", "s&p": "^GSPC", "nasdaq": "^IXIC", "dax": "^GDAXI",
    "cac 40": "^FCHI", "ftse": "^FTSE", "euro stoxx": "^STOXX50E", "wig20": "WIG20.WA",
    "eur/usd": "EURUSD=X", "eurusd": "EURUSD=X", "usd/uah": "UAH=X", "vix": "^VIX",
}
CRYPTO = {"BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE", "TON", "DOT", "LINK", "AVAX", "LTC"}
COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple", "BNB": "binancecoin",
    "ADA": "cardano", "DOGE": "dogecoin", "TON": "the-open-network", "DOT": "polkadot",
    "LINK": "chainlink", "AVAX": "avalanche-2", "LTC": "litecoin",
}


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y%m%d")


def yahoo(symbol: str, days: int = 400) -> Series:
    rng = "2y" if days > 365 else "1y" if days > 180 else "6mo"
    data = get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                    params={"range": rng, "interval": "1d"}, ttl=3600)
    try:
        res = data["chart"]["result"][0]
        stamps = res["timestamp"]
        closes = res["indicators"]["quote"][0]["close"]
        currency = res["meta"].get("currency", "")
    except (KeyError, IndexError, TypeError) as exc:
        raise FetchError(f"yahoo: no data for {symbol}") from exc
    pairs = [(_day(t), float(c)) for t, c in zip(stamps, closes) if c is not None]
    return Series(symbol, "price", [p[0] for p in pairs], [p[1] for p in pairs],
                  currency, "yahoo_finance")


def binance(symbol: str, days: int = 400) -> Series:
    rows = get_json("https://api.binance.com/api/v3/klines",
                    params={"symbol": f"{symbol}USDT", "interval": "1d",
                            "limit": min(days, 1000)}, ttl=3600)
    if not isinstance(rows, list) or not rows:
        raise FetchError(f"binance: no data for {symbol}")
    return Series(symbol, "price", [_day(r[0] / 1000) for r in rows],
                  [float(r[4]) for r in rows], "USDT", "binance")


def coingecko(symbol: str, days: int = 365) -> Series:
    coin = COINGECKO_IDS.get(symbol, symbol.lower())
    data = get_json(f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart",
                    params={"vs_currency": "usd", "days": min(days, 365), "interval": "daily"},
                    ttl=3600)
    prices = data.get("prices", []) if isinstance(data, dict) else []
    if not prices:
        raise FetchError(f"coingecko: no data for {symbol}")
    return Series(symbol, "price", [_day(p[0] / 1000) for p in prices],
                  [float(p[1]) for p in prices], "USD", "coingecko")


def resolve(name: str) -> str:
    key = name.strip().lower()
    return ALIASES.get(key, name.strip().upper())


def price_history(symbol: str, days: int = 400) -> Series:
    """Fetch daily closes; tries the next source if one fails."""
    symbol = resolve(symbol)
    if symbol in CRYPTO:
        attempts = [(binance, symbol), (coingecko, symbol), (yahoo, f"{symbol}-USD")]
    else:
        attempts = [(yahoo, symbol)]
    errors = []
    for fetch, sym in attempts:
        try:
            series = fetch(sym, days)
            series.name = symbol
            return series
        except FetchError as exc:
            errors.append(str(exc))
    raise FetchError("; ".join(errors))


def last_price(symbol: str) -> Optional[float]:
    try:
        return price_history(symbol, 10).values[-1]
    except (FetchError, IndexError):
        return None
