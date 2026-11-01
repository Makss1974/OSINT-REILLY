"""Polite HTTP layer: honest User-Agent, per-host rate limits, retries,
robots.txt for web pages and a small disk cache. No proxy rotation,
no CAPTCHA or anti-bot evasion — only openly published data."""

import hashlib
import json
import logging
import time
import urllib.robotparser
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests

from . import config

log = logging.getLogger(__name__)

# Minimal interval between requests to one host, seconds.
HOST_INTERVAL = {
    "api.gdeltproject.org": 6.0,
    "api.coingecko.com": 3.0,
    "news.google.com": 1.5,
}
DEFAULT_INTERVAL = 0.5

_session = requests.Session()
_session.headers["User-Agent"] = config.USER_AGENT
_last_call: Dict[str, float] = {}
_robots: Dict[str, urllib.robotparser.RobotFileParser] = {}
# Hosts that answered 429: we back off instead of hammering them.
_blocked_until: Dict[str, float] = {}
BACKOFF_SEC = 600


class FetchError(RuntimeError):
    pass


def _wait_turn(host: str) -> None:
    interval = HOST_INTERVAL.get(host, DEFAULT_INTERVAL)
    elapsed = time.time() - _last_call.get(host, 0.0)
    if elapsed < interval:
        time.sleep(interval - elapsed)
    _last_call[host] = time.time()


def _cache_path(key: str):
    return config.CACHE_DIR / (hashlib.sha256(key.encode("utf-8")).hexdigest()[:32] + ".json")


def _cache_get(key: str, ttl: float) -> Optional[Dict[str, Any]]:
    path = _cache_path(key)
    if ttl <= 0 or not path.exists():
        return None
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if time.time() - item.get("t", 0) > ttl:
        return None
    return item


def _cache_put(key: str, text: str, status: int) -> None:
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(key).write_text(
        json.dumps({"t": time.time(), "status": status, "text": text}), encoding="utf-8"
    )


def robots_allowed(url: str) -> bool:
    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    parser = _robots.get(base)
    if parser is None:
        parser = urllib.robotparser.RobotFileParser()
        try:
            resp = _session.get(base + "/robots.txt", timeout=15)
            parser.parse(resp.text.splitlines() if resp.status_code == 200 else [])
        except requests.RequestException:
            parser.parse([])
        _robots[base] = parser
    return parser.can_fetch(config.USER_AGENT, url)


def get_text(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    ttl: float = 900,
    retries: int = 3,
    check_robots: bool = False,
    headers: Optional[Dict[str, str]] = None,
) -> str:
    """GET a URL and return the body. Raises FetchError on failure."""
    key = url + "?" + json.dumps(params or {}, sort_keys=True)
    cached = _cache_get(key, ttl)
    if cached is not None:
        return cached["text"]
    if check_robots and not robots_allowed(url):
        raise FetchError(f"robots.txt disallows {url}")

    host = urlparse(url).netloc
    if _blocked_until.get(host, 0) > time.time():
        raise FetchError(f"{host}: rate limited (HTTP 429), skipped for now")
    last_error = ""
    for attempt in range(retries):
        _wait_turn(host)
        try:
            resp = _session.get(url, params=params, timeout=30, headers=headers)
        except requests.RequestException as exc:
            last_error = str(exc)
        else:
            if resp.status_code == 200:
                _cache_put(key, resp.text, resp.status_code)
                return resp.text
            last_error = f"HTTP {resp.status_code}: {resp.text[:120]}"
            if resp.status_code == 429 and attempt >= 1:
                _blocked_until[host] = time.time() + BACKOFF_SEC
                raise FetchError(f"{host}: rate limited (HTTP 429)")
            if resp.status_code not in (429, 500, 502, 503, 504):
                break
        time.sleep(HOST_INTERVAL.get(host, 2.0) * (attempt + 1))
    raise FetchError(f"{host}: {last_error}")


def get_json(url: str, params: Optional[Dict[str, Any]] = None, ttl: float = 900, **kw) -> Any:
    text = get_text(url, params=params, ttl=ttl, **kw)
    try:
        return json.loads(text)
    except ValueError as exc:
        raise FetchError(f"{urlparse(url).netloc}: not JSON ({text[:80]!r})") from exc


def post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 90) -> Any:
    host = urlparse(url).netloc
    _wait_turn(host)
    try:
        resp = _session.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        raise FetchError(f"{host}: {exc}") from exc
    if resp.status_code != 200:
        raise FetchError(f"{host}: HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.json()
