"""Natural hazards, all open data without keys:
- GDACS (UN / EC JRC global disaster alerts)
- USGS earthquakes
- NASA EONET open natural events (wildfires, storms, volcanoes, floods)
- Open-Meteo: weather forecast, GloFAS river discharge, air quality
- NOAA SWPC planetary Kp forecast (geomagnetic storms)
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..http import get_json, get_text

# lon_min, lon_max, lat_min, lat_max
REGIONS = {
    "PL": (14.0, 24.2, 49.0, 55.0),
    "UA": (22.0, 40.3, 44.3, 52.4),
    "EUROPE": (-25.0, 45.0, 34.0, 72.0),
}
GDACS_NS = {"gdacs": "http://www.gdacs.org", "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#"}


def region_of(lon: float, lat: float) -> str:
    for name, (x0, x1, y0, y1) in REGIONS.items():
        if x0 <= lon <= x1 and y0 <= lat <= y1:
            return name
    return "WORLD"


def gdacs() -> List[Dict[str, Any]]:
    root = ET.fromstring(get_text("https://www.gdacs.org/xml/rss.xml", ttl=3600).lstrip("﻿"))
    out = []
    for it in root.iter("item"):
        try:
            lat = float(it.findtext("geo:Point/geo:lat", namespaces=GDACS_NS))
            lon = float(it.findtext("geo:Point/geo:long", namespaces=GDACS_NS))
        except (TypeError, ValueError):
            continue
        out.append({
            "source": "GDACS", "type": it.findtext("gdacs:eventtype", namespaces=GDACS_NS),
            "level": it.findtext("gdacs:alertlevel", namespaces=GDACS_NS) or "",
            "title": it.findtext("title") or "", "url": it.findtext("link") or "",
            "country": it.findtext("gdacs:country", namespaces=GDACS_NS) or "",
            "date": (it.findtext("gdacs:fromdate", namespaces=GDACS_NS) or "")[:16],
            "current": (it.findtext("gdacs:iscurrent", namespaces=GDACS_NS) or "") == "true",
            "lat": lat, "lon": lon, "region": region_of(lon, lat),
        })
    return out


def earthquakes() -> List[Dict[str, Any]]:
    data = get_json("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson",
                    ttl=1800)
    out = []
    for f in data.get("features", []):
        p, (lon, lat, depth) = f["properties"], f["geometry"]["coordinates"][:3]
        out.append({
            "source": "USGS", "type": "EQ", "magnitude": p.get("mag"), "title": p.get("title", ""),
            "url": p.get("url", ""), "level": (p.get("alert") or "").capitalize(),
            "date": datetime.fromtimestamp(p["time"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "tsunami": bool(p.get("tsunami")), "depth_km": depth,
            "lat": lat, "lon": lon, "region": region_of(lon, lat),
        })
    return out


def eonet(days: int = 30) -> List[Dict[str, Any]]:
    data = get_json("https://eonet.gsfc.nasa.gov/api/v3/events",
                    params={"status": "open", "days": days}, ttl=3600)
    out = []
    for e in data.get("events", []):
        geo = e.get("geometry") or []
        if not geo or geo[-1].get("type") != "Point":
            continue
        lon, lat = geo[-1]["coordinates"][:2]
        out.append({
            "source": "NASA EONET", "type": (e.get("categories") or [{}])[0].get("id", ""),
            "title": e.get("title", ""), "url": e.get("link", ""), "level": "",
            "date": (geo[-1].get("date") or "")[:16], "lat": lat, "lon": lon,
            "region": region_of(lon, lat),
        })
    return out


def weather(lat: float, lon: float, days: int = 10) -> Dict[str, List]:
    data = get_json("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lat, "longitude": lon, "forecast_days": days, "timezone": "auto",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                 "wind_gusts_10m_max,relative_humidity_2m_min",
    }, ttl=3600)
    return data["daily"]


def river(lat: float, lon: float) -> Dict[str, List]:
    """GloFAS river discharge: past 60 days + 30-day ensemble forecast."""
    data = get_json("https://flood-api.open-meteo.com/v1/flood", params={
        "latitude": lat, "longitude": lon, "past_days": 60, "forecast_days": 30,
        "daily": "river_discharge,river_discharge_max",
    }, ttl=10800)
    return data["daily"]


def air_quality(lat: float, lon: float) -> Dict[str, List]:
    data = get_json("https://air-quality-api.open-meteo.com/v1/air-quality", params={
        "latitude": lat, "longitude": lon, "forecast_days": 4,
        "hourly": "european_aqi,pm2_5"}, ttl=3600)
    return data["hourly"]


def kp_forecast() -> List[Dict[str, Any]]:
    rows = get_json("https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json",
                    ttl=3600)
    if rows and isinstance(rows[0], list):  # older format: header row + lists
        head = rows[0]
        rows = [dict(zip(head, r)) for r in rows[1:]]
    return [{"time": r["time_tag"], "kp": float(r["kp"]), "observed": r.get("observed", "")}
            for r in rows]
