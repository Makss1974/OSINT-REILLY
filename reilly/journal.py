"""Forecast journal: every probability REILLY gives is written down and later
scored (Brier score, hit rate). Market forecasts resolve automatically from
prices; hypothesis forecasts are resolved by the analyst (yes / no)."""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from . import config
from .collectors.markets import last_price


def _load() -> List[Dict[str, Any]]:
    if not config.FORECASTS_FILE.exists():
        return []
    rows = []
    for line in config.FORECASTS_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _save(rows: List[Dict[str, Any]]) -> None:
    config.FORECASTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.FORECASTS_FILE.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def record(kind: str, question: str, probability: float, horizon_days: int,
           **extra: Any) -> str:
    rows = _load()
    fid = uuid.uuid4().hex[:8]
    rows.append({
        "id": fid, "kind": kind, "question": question,
        "p": round(probability, 4), "created": time.time(),
        "due": time.time() + horizon_days * 86400, "outcome": None, **extra,
    })
    _save(rows)
    return fid


def resolve(fid: str, outcome: bool) -> bool:
    rows = _load()
    for r in rows:
        if r["id"] == fid:
            r["outcome"] = int(outcome)
            r["resolved"] = time.time()
            _save(rows)
            return True
    return False


def auto_resolve() -> int:
    """Resolve matured market forecasts: did the price end above the start?"""
    rows = _load()
    done = 0
    for r in rows:
        if r["outcome"] is None and r["kind"] == "market_up" and time.time() >= r["due"]:
            price = last_price(r["asset"])
            if price is not None:
                r["outcome"] = int(price > r["start_price"])
                r["end_price"] = price
                r["resolved"] = time.time()
                done += 1
    if done:
        _save(rows)
    return done


def scoreboard() -> Dict[str, Any]:
    rows = _load()
    resolved = [r for r in rows if r["outcome"] is not None]
    brier = sum((r["p"] - r["outcome"]) ** 2 for r in resolved) / len(resolved) if resolved else None
    hits = sum(1 for r in resolved if (r["p"] >= 0.5) == bool(r["outcome"]))
    return {
        "total": len(rows),
        "resolved": len(resolved),
        "open": [r for r in rows if r["outcome"] is None],
        "brier": round(brier, 4) if brier is not None else None,
        "brier_baseline": 0.25,  # always answering 50 %
        "hit_rate": round(hits / len(resolved), 3) if resolved else None,
        "rows": rows,
    }


def fmt_date(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
