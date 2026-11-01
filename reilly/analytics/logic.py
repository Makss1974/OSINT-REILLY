"""Logical layer: Bayesian update of a hypothesis from collected evidence.

The analyst states a hypothesis, its polarity and a prior probability:
  polarity "risk"     — something bad happens / escalates (crisis, default, price falls)
  polarity "positive" — something good happens (deal, recovery, price rises)
Each evidence item adds a log-likelihood ratio (LLR) to the prior log-odds.
Weights are explicit and deliberately modest; their calibration is checked
over time by the forecast journal (Brier score), not assumed.
"""

import math
from typing import Any, Dict, List, Optional


def logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def evaluate(prior: float, polarity: str, methods: Dict[str, Any],
             news_volume: Optional[Dict[str, Any]], news_tone: Optional[Dict[str, Any]],
             crisis_chain: Optional[Dict[str, Any]],
             market_returns: Dict[str, float], asset_direction: str = "auto") -> Dict[str, Any]:
    """asset_direction: which move of the linked assets supports the hypothesis
    ("up" / "down"); "auto" = down for risk, up for positive. E.g. "gas price
    spikes" is a risk whose supporting asset move is up."""
    sign = 1.0 if polarity == "risk" else -1.0
    if asset_direction == "auto":
        asset_direction = "down" if polarity == "risk" else "up"
    asset_sign = 1.0 if asset_direction == "up" else -1.0
    evidence: List[Dict[str, Any]] = []

    def add(name: str, value: Any, llr: float) -> None:
        evidence.append({"evidence": name, "value": value, "llr": round(llr, 3)})

    s = methods.get("weighted_sentiment", 0.0) if methods else 0.0
    if methods:
        add("news_sentiment", s, sign * -1.2 * s)
        add("linguistic_stress", methods["linguistic_stress_index"],
            sign * 2.0 * methods["linguistic_stress_index"])
        add("goldratt_constraints", methods["goldratt_constraint_index"],
            sign * 1.5 * methods["goldratt_constraint_index"])
    if news_volume and news_volume.get("points"):
        z = news_volume.get("z_last", 0.0)
        direction = -1.0 if s > 0.05 else 1.0  # a surge amplifies the dominant tone
        add("coverage_surge_z", z, sign * direction * 0.15 * clip(z, 0, 4))
    if news_tone and news_tone.get("points"):
        slope = news_tone["trend"]["slope"]
        add("tone_trend_per_day", round(slope, 4), sign * clip(-8.0 * slope, -0.6, 0.6))
    if crisis_chain:
        # only the deviation from the series' own base rate is evidence
        p, base = crisis_chain["p_crisis_day_in_horizon"], crisis_chain["p_crisis_base"]
        add("markov_p_crisis_vs_base", f"{p} / {base}",
            sign * clip(0.5 * (logit(p) - logit(base)), -0.6, 0.6))
    if market_returns:
        avg = sum(market_returns.values()) / len(market_returns)
        add(f"linked_assets_30d ({asset_direction})", round(avg, 4),
            clip(asset_sign * 5.0 * avg, -0.8, 0.8))

    reliability = 0.5 + 0.5 * methods.get("verified_share", 0.0) if methods else 0.5
    total = sum(e["llr"] for e in evidence) * reliability
    posterior = sigmoid(logit(prior) + total)
    return {
        "prior": round(prior, 3),
        "posterior": round(posterior, 3),
        "reliability_factor": round(reliability, 2),
        "total_llr": round(total, 3),
        "evidence": evidence,
    }
