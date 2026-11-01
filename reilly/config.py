"""Paths and settings. All paths are relative to the project root."""

import json
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


def update_env(values: dict) -> None:
    """Write keys into .env (never committed) and apply them to this process."""
    global OPENROUTER_TOKEN, OPENROUTER_MODEL, CONTACT
    path = ROOT / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    for key, value in values.items():
        row = f"{key}={value}"
        hits = [i for i, line in enumerate(lines) if line.split("=", 1)[0].strip() == key]
        if hits:
            lines[hits[0]] = row
        else:
            lines.append(row)
        os.environ[key] = value
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OPENROUTER_TOKEN = env("OPENROUTER_API_TOKEN", "OPENROUTER_API_KEY")
    OPENROUTER_MODEL = env("OPENROUTER_MODEL")
    CONTACT = env("REILLY_CONTACT")


def ensure_dirs() -> None:
    for d in (CACHE_DIR, REPORTS_DIR, PAGES_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


SETTINGS_FILE = STATE / "settings.json"


def saved_lang() -> str:
    """Language chosen in the UI, else REILLY_LANG from .env, else English."""
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8")).get("lang", DEFAULT_LANG)
    except (OSError, ValueError):
        return DEFAULT_LANG


def save_lang(lang: str) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps({"lang": lang}), encoding="utf-8")
