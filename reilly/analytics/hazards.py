"""Hazard early warning from forecasts and alert feeds.

Thresholds follow common meteorological warning practice (IMGW / Ukrhydromet
style 1st-3rd degree, simplified). Earthquakes are NOT predicted — only
current activity is reported; that is the honest state of science.

Levels: WATCH (1) < WARNING (2) < DANGER (3)
"""

from collections import Counter
from typing import Any, Dict, List, Optional

LEVELS = {1: "WATCH", 2: "WARNING", 3: "DANGER"}

# (hazard, field, comparison, thresholds for levels 1, 2, 3)
WEATHER_RULES = [
    ("heat", "temperature_2m_max", ">=", (30.0, 34.0, 38.0)),
    ("frost", "temperature_2m_min", "<=", (-15.0, -20.0, -27.0)),
    ("wind", "wind_gusts_10m_max", ">=", (70.0, 90.0, 110.0)),
    ("heavy_rain", "precipitation_sum", ">=", (30.0, 50.0, 80.0)),
]


def _level(value: Optional[float], op: str, thresholds) -> int:
    if value is None:
        return 0
    hit = (lambda t: value >= t) if op == ">=" else (lambda t: value <= t)
    return max((i + 1 for i, t in enumerate(thresholds) if hit(t)), default=0)


def weather_alerts(location: str, daily: Dict[str, List]) -> List[Dict[str, Any]]:
    out = []
    days = daily.get("time", [])
    for hazard, field, op, thr in WEATHER_RULES:
        for d, v in zip(days, daily.get(field, [])):
            lvl = _level(v, op, thr)
            if lvl:
                out.append({"location": location, "hazard": hazard, "date": d, "value": v,
                            "level": LEVELS[lvl], "source": "Open-Meteo"})
    # fire weather: hot, dry, windy, no rain (simplified Angström-style rule)
    for i, d in enumerate(days):
        t = daily.get("temperature_2m_max", [None])[i]
        rh = daily.get("relative_humidity_2m_min", [None])[i]
        rain = daily.get("precipitation_sum", [None])[i]
        gust = daily.get("wind_gusts_10m_max", [None])[i]
        if None in (t, rh, rain, gust) or rain >= 1.0 or t < 24 or rh > 35:
            continue
        lvl = 1 + (rh <= 25) + (gust >= 40 and t >= 28)
        out.append({"location": location, "hazard": "fire_weather", "date": d,
                    "value": f"T{t:.0f} RH{rh:.0f}% G{gust:.0f}", "level": LEVELS[lvl],
                    "source": "Open-Meteo"})
    return out


def flood_alerts(location: str, river_name: str, daily: Dict[str, List],
                 min_mean: float = 5.0) -> List[Dict[str, Any]]:
    """Forecast discharge vs the median of the past 60 days (GloFAS)."""
    times = daily.get("time", [])
    q = daily.get("river_discharge", [])
    qmax = daily.get("river_discharge_max", []) or q
    past = sorted(v for v, t in zip(q[:60], times[:60]) if v is not None)
    if len(past) < 20:
        return []
    median = past[len(past) // 2]
    if median < min_mean:
        return []  # grid point is not on a real river
    out = []
    for t, v, vmax in zip(times[60:], q[60:], qmax[60:]):
        if v is None:
            continue
        ratio, ratio_max = v / median, (vmax or v) / median
        lvl = 3 if ratio >= 4 else 2 if ratio >= 2.5 else 1 if ratio >= 1.8 or ratio_max >= 3 else 0
        if lvl:
            out.append({"location": f"{location} ({river_name})", "hazard": "flood", "date": t,
                        "value": f"x{ratio:.1f} (max x{ratio_max:.1f})", "level": LEVELS[lvl],
                        "source": "GloFAS"})
    return out


def air_alerts(location: str, hourly: Dict[str, List]) -> List[Dict[str, Any]]:
    worst: Dict[str, float] = {}
    for t, aqi in zip(hourly.get("time", []), hourly.get("european_aqi", [])):
        if aqi is not None:
            day = t[:10]
            worst[day] = max(worst.get(day, 0), aqi)
    return [{"location": location, "hazard": "air_quality", "date": d, "value": round(v),
             "level": LEVELS[3 if v >= 100 else 2 if v >= 80 else 1], "source": "CAMS"}
            for d, v in worst.items() if v >= 60]


def kp_alerts(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """NOAA G-scale: Kp 5 = G1, 6 = G2, 7+ = G3 and above."""
    out = []
    for r in rows:
        if r["observed"] == "observed":
            continue
        lvl = 3 if r["kp"] >= 7 else 2 if r["kp"] >= 6 else 1 if r["kp"] >= 5 else 0
        if lvl:
            out.append({"location": "Earth", "hazard": "geomagnetic_storm", "date": r["time"][:13],
                        "value": f"Kp {r['kp']:.1f}", "level": LEVELS[lvl], "source": "NOAA SWPC"})
    return out


def event_alerts(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Current disaster events: everything in PL / UA / Europe, Orange/Red worldwide."""
    out = []
    for e in events:
        level = (e.get("level") or "").lower()
        big_quake = e.get("type") == "EQ" and (e.get("magnitude") or 0) >= 6.0
        if e["region"] == "WORLD" and level not in ("orange", "red") and not big_quake:
            continue
        if e["source"] == "GDACS" and not e.get("current", True):
            continue
        lvl = 3 if level == "red" else 2 if level == "orange" or big_quake else 1
        out.append({"location": e["region"] if e["region"] != "WORLD" else e.get("country") or "WORLD",
                    "hazard": e["type"], "date": e["date"], "value": e["title"][:90],
                    "level": LEVELS[lvl], "source": e["source"], "url": e.get("url", "")})
    return out


def summarize(alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    order = {"DANGER": 3, "WARNING": 2, "WATCH": 1}
    alerts.sort(key=lambda a: (-order[a["level"]], a["date"]))
    by_level = Counter(a["level"] for a in alerts)
    by_hazard = Counter(a["hazard"] for a in alerts)
    return {"total": len(alerts), "by_level": dict(by_level), "by_hazard": dict(by_hazard),
            "alerts": alerts}
