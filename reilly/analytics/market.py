"""Quantitative market analytics for stocks, indices, commodities, FX, crypto.

Everything is computed from daily closes:
- return / risk: CAGR-like annualised return, volatility, Sharpe, max drawdown,
  historical VaR / CVaR (95 %)
- technicals: SMA 50/200, RSI(14), MACD(12,26,9), Bollinger %B
- persistence: Hurst exponent (rescaled range) — >0.5 trending, <0.5 mean-reverting
- regimes: empirical Markov chain over DOWN / FLAT / UP days
- forecast: Monte-Carlo bootstrap of historical returns -> P(up), price quantiles
"""

from typing import Any, Dict, List, Optional

import numpy as np

TRADING_DAYS = 252
CRYPTO_DAYS = 365


def log_returns(prices: np.ndarray) -> np.ndarray:
    prices = np.asarray(prices, dtype=float)
    return np.diff(np.log(prices))


def max_drawdown(prices: np.ndarray) -> float:
    prices = np.asarray(prices, dtype=float)
    peaks = np.maximum.accumulate(prices)
    return float(np.min(prices / peaks - 1.0))


def ema(values: np.ndarray, span: int) -> np.ndarray:
    alpha = 2.0 / (span + 1.0)
    out = np.empty(len(values))
    out[0] = values[0]
    for i in range(1, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def rsi(prices: np.ndarray, period: int = 14) -> float:
    """Wilder's RSI of the last value."""
    delta = np.diff(np.asarray(prices, dtype=float))
    if len(delta) < period:
        return float("nan")
    gains, losses = np.clip(delta, 0, None), np.clip(-delta, 0, None)
    avg_gain, avg_loss = gains[:period].mean(), losses[:period].mean()
    for g, l in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
    if avg_loss == 0:
        return 100.0
    return float(100 - 100 / (1 + avg_gain / avg_loss))


def macd(prices: np.ndarray) -> Dict[str, float]:
    prices = np.asarray(prices, dtype=float)
    line = ema(prices, 12) - ema(prices, 26)
    signal = ema(line, 9)
    return {"macd": float(line[-1]), "signal": float(signal[-1]),
            "histogram": float(line[-1] - signal[-1])}


def bollinger_b(prices: np.ndarray, window: int = 20) -> float:
    w = np.asarray(prices[-window:], dtype=float)
    mid, sd = w.mean(), w.std(ddof=1)
    if sd == 0:
        return 0.5
    return float((w[-1] - (mid - 2 * sd)) / (4 * sd))


def hurst(prices: np.ndarray) -> float:
    """Hurst exponent by rescaled-range analysis of log returns."""
    r = log_returns(prices)
    n = len(r)
    if n < 64:
        return float("nan")
    sizes = np.unique(np.floor(np.logspace(np.log10(8), np.log10(n // 2), 10)).astype(int))
    rs = []
    for size in sizes:
        chunks = r[: (n // size) * size].reshape(-1, size)
        dev = np.cumsum(chunks - chunks.mean(axis=1, keepdims=True), axis=1)
        spread = dev.max(axis=1) - dev.min(axis=1)
        sd = chunks.std(axis=1, ddof=1)
        ok = sd > 0
        rs.append(np.mean(spread[ok] / sd[ok]))
    slope = np.polyfit(np.log(sizes), np.log(rs), 1)[0]
    return float(slope)


def var_cvar(returns: np.ndarray, level: float = 0.95) -> Dict[str, float]:
    q = np.quantile(returns, 1 - level)
    tail = returns[returns <= q]
    return {"var": float(q), "cvar": float(tail.mean() if len(tail) else q)}


STATES = ("DOWN", "FLAT", "UP")


def markov_regimes(returns: np.ndarray, horizon: int = 20) -> Dict[str, Any]:
    """Empirical 3-state Markov chain of daily moves (threshold ±0.5σ)."""
    sigma = returns.std(ddof=1)
    states = np.where(returns > 0.5 * sigma, 2, np.where(returns < -0.5 * sigma, 0, 1))
    counts = np.ones((3, 3))  # Laplace smoothing
    for a, b in zip(states[:-1], states[1:]):
        counts[a, b] += 1
    matrix = counts / counts.sum(axis=1, keepdims=True)
    current = np.zeros(3)
    current[states[-1]] = 1.0
    future = current @ np.linalg.matrix_power(matrix, horizon)
    # stationary distribution = eigenvector for eigenvalue 1
    vals, vecs = np.linalg.eig(matrix.T)
    stat = np.real(vecs[:, np.argmin(np.abs(vals - 1))])
    stat = stat / stat.sum()
    return {
        "current_state": STATES[states[-1]],
        "transition_matrix": {STATES[i]: {STATES[j]: round(float(matrix[i, j]), 3)
                                          for j in range(3)} for i in range(3)},
        "distribution_in_horizon": {STATES[i]: round(float(future[i]), 3) for i in range(3)},
        "stationary": {STATES[i]: round(float(stat[i]), 3) for i in range(3)},
        "persistence_up": round(float(matrix[2, 2]), 3),
        "persistence_down": round(float(matrix[0, 0]), 3),
    }


def monte_carlo(prices: np.ndarray, horizon: int, paths: int = 5000,
                seed: Optional[int] = 7, lookback: int = 500) -> Dict[str, Any]:
    """Stationary bootstrap of recent log returns -> distribution of the price."""
    r = log_returns(prices)[-lookback:]
    rng = np.random.default_rng(seed)
    block = 5  # keep short-term autocorrelation / volatility clusters
    n_blocks = int(np.ceil(horizon / block))
    starts = rng.integers(0, len(r) - block, size=(paths, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)).reshape(paths, -1)[:, :horizon]
    total = r[idx].sum(axis=1)
    last = float(prices[-1])
    final = last * np.exp(total)
    q = np.quantile(final, [0.05, 0.25, 0.5, 0.75, 0.95])
    return {
        "horizon_days": horizon,
        "p_up": round(float((final > last).mean()), 3),
        "p_drop_10pct": round(float((final < last * 0.9).mean()), 3),
        "p_rise_10pct": round(float((final > last * 1.1).mean()), 3),
        "quantiles": {k: round(float(v), 4) for k, v in zip(("p05", "p25", "p50", "p75", "p95"), q)},
    }


def analyze_prices(name: str, dates: List[str], prices: List[float],
                   horizon: int = 30, crypto: bool = False) -> Dict[str, Any]:
    p = np.asarray(prices, dtype=float)
    if len(p) < 60:
        return {"asset": name, "error": f"too little history ({len(p)} days)"}
    r = log_returns(p)
    year = CRYPTO_DAYS if crypto else TRADING_DAYS
    ann_ret = float(np.exp(r.mean() * year) - 1)
    ann_vol = float(r.std(ddof=1) * np.sqrt(year))
    sma50 = float(p[-50:].mean())
    sma200 = float(p[-200:].mean()) if len(p) >= 200 else float("nan")
    if np.isnan(sma200):
        trend = "UP" if p[-1] > sma50 else "DOWN"
    elif p[-1] > sma50 > sma200:
        trend = "UP"
    elif p[-1] < sma50 < sma200:
        trend = "DOWN"
    else:
        trend = "MIXED"
    horizon_bars = max(1, round(horizon * (year / 365)))
    return {
        "asset": name,
        "last_date": dates[-1],
        "last": round(float(p[-1]), 4),
        "change_30d": round(float(p[-1] / p[-min(len(p), 22 if not crypto else 31)] - 1), 4),
        "change_1y": round(float(p[-1] / p[-min(len(p), year + 1)] - 1), 4),
        "ann_return": round(ann_ret, 4),
        "ann_volatility": round(ann_vol, 4),
        "sharpe": round(ann_ret / ann_vol, 2) if ann_vol else None,
        "max_drawdown": round(max_drawdown(p[-year:]), 4),
        **{k: round(v, 4) for k, v in var_cvar(r[-year:]).items()},
        "rsi14": round(rsi(p), 1),
        "macd": {k: round(v, 4) for k, v in macd(p).items()},
        "bollinger_b": round(bollinger_b(p), 2),
        "sma50": round(sma50, 4),
        "sma200": None if np.isnan(sma200) else round(sma200, 4),
        "trend": trend,
        "hurst": round(hurst(p), 3),
        "markov": markov_regimes(r[-year * 2:], horizon_bars),
        "monte_carlo": monte_carlo(p, horizon_bars),
    }


def correlation_matrix(series: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Pearson correlation of daily log returns on common dates."""
    names = list(series)
    common = sorted(set.intersection(*(set(s) for s in series.values()))) if names else []
    if len(common) < 30:
        return {}
    mat = np.array([[series[n][d] for d in common] for n in names])
    rets = np.diff(np.log(mat), axis=1)
    corr = np.corrcoef(rets)
    return {a: {b: round(float(corr[i, j]), 2) for j, b in enumerate(names)}
            for i, a in enumerate(names)}
