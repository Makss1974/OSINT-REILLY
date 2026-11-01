"""Generic time-series tools for news volume, attention and macro data:
robust anomaly detection, linear trend, Holt forecasting and growth rates."""

from typing import Any, Dict, List, Sequence

import numpy as np


def robust_z(values: Sequence[float], window: int = 28) -> np.ndarray:
    """Z-score of each point vs. the median/MAD of the preceding window."""
    v = np.asarray(values, dtype=float)
    z = np.zeros(len(v))
    for i in range(len(v)):
        past = v[max(0, i - window):i]
        if len(past) < 7:
            continue
        med = np.median(past)
        mad = np.median(np.abs(past - med)) * 1.4826
        scale = mad if mad > 0 else (past.std() or 1.0)
        z[i] = (v[i] - med) / scale
    return z


def anomalies(dates: List[str], values: Sequence[float], threshold: float = 3.0) -> List[Dict]:
    z = robust_z(values)
    return [{"date": d, "value": round(float(x), 2), "z": round(float(s), 2)}
            for d, x, s in zip(dates, values, z) if abs(s) >= threshold]


def linear_trend(values: Sequence[float]) -> Dict[str, float]:
    """OLS slope per step, relative slope and R²."""
    y = np.asarray(values, dtype=float)
    if len(y) < 3:
        return {"slope": 0.0, "rel_slope": 0.0, "r2": 0.0}
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    fit = slope * x + intercept
    ss_res, ss_tot = ((y - fit) ** 2).sum(), ((y - y.mean()) ** 2).sum()
    mean = abs(y.mean()) or 1.0
    return {"slope": float(slope), "rel_slope": float(slope / mean),
            "r2": float(1 - ss_res / ss_tot) if ss_tot else 0.0}


def holt_forecast(values: Sequence[float], steps: int = 3, alpha: float = 0.7,
                  beta: float = 0.2, phi: float = 0.85) -> Dict[str, Any]:
    """Damped-trend Holt exponential smoothing with a residual-based 80 % band.
    phi < 1 fades the trend out, which suits mean-reverting macro series."""
    y = np.asarray(values, dtype=float)
    if len(y) < 4:
        return {"forecast": [], "band": []}
    level, trend = y[0], y[1] - y[0]
    errors = []
    for t in range(1, len(y)):
        prediction = level + phi * trend
        errors.append(y[t] - prediction)
        new_level = alpha * y[t] + (1 - alpha) * (level + phi * trend)
        trend = beta * (new_level - level) + (1 - beta) * phi * trend
        level = new_level
    sd = float(np.std(errors[1:], ddof=1)) if len(errors) > 2 else 0.0
    fc = [float(level + trend * sum(phi ** i for i in range(1, h + 1)))
          for h in range(1, steps + 1)]
    band = [(round(f - 1.28 * sd * np.sqrt(h), 3), round(f + 1.28 * sd * np.sqrt(h), 3))
            for h, f in enumerate(fc, 1)]
    return {"forecast": [round(f, 3) for f in fc], "band": band}


def cagr(first: float, last: float, periods: int) -> float:
    if first <= 0 or last <= 0 or periods <= 0:
        return float("nan")
    return (last / first) ** (1 / periods) - 1


def summarize_series(dates: List[str], values: Sequence[float]) -> Dict[str, Any]:
    v = np.asarray(values, dtype=float)
    if len(v) == 0:
        return {"points": 0}
    recent, base = v[-7:], v[:-7] if len(v) > 14 else v
    z_last = float(robust_z(v)[-1]) if len(v) > 8 else 0.0
    return {
        "points": int(len(v)),
        "first_date": dates[0], "last_date": dates[-1],
        "last": round(float(v[-1]), 3),
        "mean": round(float(v.mean()), 3),
        "recent_vs_base": round(float(recent.mean() / base.mean() - 1), 3) if base.mean() else None,
        "z_last": round(z_last, 2),
        "trend": {k: round(x, 4) for k, x in linear_trend(v).items()},
        "anomalies": anomalies(dates, v)[-10:],
    }


def regime_chain(values: Sequence[float], horizon: int = 30) -> Dict[str, Any]:
    """Markov chain over CALM / ELEVATED / CRISIS states of a news or
    attention series (robust z < 1, 1..3, >= 3); probability of CRISIS ahead."""
    z = robust_z(values)[7:]
    if len(z) < 20:
        return {}
    s = np.where(z >= 3, 2, np.where(z >= 1, 1, 0))
    counts = np.ones((3, 3))
    for a, b in zip(s[:-1], s[1:]):
        counts[a, b] += 1
    m = counts / counts.sum(axis=1, keepdims=True)
    start = np.zeros(3)
    start[s[-1]] = 1
    names = ("CALM", "ELEVATED", "CRISIS")
    # probability of visiting CRISIS at least once within the horizon
    absorbing = m.copy()
    absorbing[2] = [0, 0, 1]
    reach = np.linalg.matrix_power(absorbing, horizon)
    hit = (start @ reach)[2]
    # base rate: same probability when starting from the long-run state mix
    vals, vecs = np.linalg.eig(m.T)
    stat = np.real(vecs[:, np.argmin(np.abs(vals - 1))])
    base = (stat / stat.sum()) @ reach
    return {
        "current_state": names[s[-1]],
        "p_crisis_day_in_horizon": round(float(hit), 3),
        "p_crisis_base": round(float(base[2]), 3),
        "transition_matrix": {names[i]: {names[j]: round(float(m[i, j]), 3) for j in range(3)}
                              for i in range(3)},
    }
