"""Paths and settings. All paths are relative to the project root."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
CACHE_DIR = STATE / "cache"
REPORTS_DIR = STATE / "reports"
PAGES_DIR = STATE / "pages"
FORECASTS_FILE = STATE / "forecasts.jsonl"
LOG_DIR = ROOT / "logs"

load_dotenv(ROOT / ".env")


def env(name: str, *aliases: str) -> str:
    for key in (name, *aliases):
        value = (os.getenv(key) or "").strip()
        if value:
            return value
    return ""


OPENROUTER_TOKEN = env("OPENROUTER_API_TOKEN", "OPENROUTER_API_KEY")
OPENROUTER_MODEL = env("OPENROUTER_MODEL")
BRIGHTDATA_TOKEN = env("BRIGHTDATA_API_TOKEN")
BRIGHTDATA_SERP_ZONE = env("BRIGHTDATA_SERP_ZONE")
CONTACT = env("REILLY_CONTACT")
DEFAULT_LANG = env("REILLY_LANG").lower() or "en"

USER_AGENT = "OSINT-REILLY/5.0 (open-source research tool" + (f"; {CONTACT})" if CONTACT else ")")


def ensure_dirs() -> None:
    for d in (CACHE_DIR, REPORTS_DIR, PAGES_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
