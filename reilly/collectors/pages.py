"""Page monitor: fetch user-given public pages (robots.txt respected),
keep a text snapshot and report what changed since the previous run."""

import difflib
import hashlib
import html
import json
import re
import time
from typing import Any, Dict

from .. import config
from ..http import get_text

_SCRIPT = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def visible_text(raw_html: str) -> str:
    text = html.unescape(_TAG.sub("\n", _SCRIPT.sub(" ", raw_html)))
    lines = (re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines())
    return "\n".join(ln for ln in lines if len(ln) > 2)


def check_page(url: str) -> Dict[str, Any]:
    text = visible_text(get_text(url, ttl=0, check_robots=True))
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    config.PAGES_DIR.mkdir(parents=True, exist_ok=True)
    snap = config.PAGES_DIR / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".json")

    previous = None
    if snap.exists():
        previous = json.loads(snap.read_text(encoding="utf-8"))
    result: Dict[str, Any] = {"url": url, "hash": digest, "chars": len(text),
                              "status": "NEW_BASELINE", "added": [], "removed": []}
    if previous:
        if previous["hash"] == digest:
            result["status"] = "UNCHANGED"
        else:
            diff = list(difflib.unified_diff(previous["text"].splitlines(),
                                             text.splitlines(), lineterm="", n=0))
            result["status"] = "CHANGED"
            result["added"] = [d[1:] for d in diff if d.startswith("+") and not d.startswith("+++")][:20]
            result["removed"] = [d[1:] for d in diff if d.startswith("-") and not d.startswith("---")][:20]
        result["previous_check"] = previous["t"]
    snap.write_text(json.dumps({"url": url, "t": time.time(), "hash": digest, "text": text},
                               ensure_ascii=False), encoding="utf-8")
    return result
