#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 4 — Analytics Orchestrator
Path: block4_main.py
Line Length Limit: 100 characters

Integration contract:
  INPUT  ← ./state/collection_result.json  (block2_main.py output)
  OUTPUT → ./state/analytics_result.json   (passed to block5_main.py)
"""

import json
import logging
import os
import sys
import argparse
from dotenv import load_dotenv

from core_intelligence.router import ReillyLlmRouter
from core_intelligence.analytics.analytics_engine import AnalyticsEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

STATE_DIR             = "./state"
COLLECTION_RESULT_FILE = os.path.join(STATE_DIR, "collection_result.json")
ANALYTICS_RESULT_FILE  = os.path.join(STATE_DIR, "analytics_result.json")


def run_block4(collection_result: dict) -> dict:
    """Запускає повний аналітичний конвеєр."""
    load_dotenv()
    router = ReillyLlmRouter()
    engine = AnalyticsEngine(router=router)

    logger.info("=" * 60)
    logger.info("OSINT-REILLY | Block 4 Analytics START")
    logger.info("=" * 60)

    analytics_result = engine.analyze(collection_result)

    # Збереження для Block 5
    os.makedirs(STATE_DIR, exist_ok=True)
    try:
        with open(ANALYTICS_RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(analytics_result, f, ensure_ascii=False, indent=2)
        logger.info("Analytics result saved → %s", ANALYTICS_RESULT_FILE)
    except OSError as exc:
        logger.error("Cannot save analytics result: %s", exc)

    logger.info("=" * 60)
    logger.info("OSINT-REILLY | Block 4 Analytics COMPLETE ✅")
    logger.info("=" * 60)
    return analytics_result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run OSINT-REILLY Block 4 — Analytics"
    )
    parser.add_argument(
        "collection_result_file",
        nargs="?",
        default=COLLECTION_RESULT_FILE,
        help="Path to CollectionResult JSON (Block 2 output)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.collection_result_file):
        logger.critical(
            "CollectionResult not found: %s  "
            "Run block2_main.py first.", args.collection_result_file
        )
        sys.exit(1)

    with open(args.collection_result_file, "r", encoding="utf-8") as f:
        collection_result = json.load(f)

    result = run_block4(collection_result)

    print("\n" + "=" * 60)
    print("BLOCK 4 SYNTHESIS OUTPUT")
    print("=" * 60)
    synthesis = result.get("synthesis", {})
    print(f"THREAT LEVEL      : {synthesis.get('threat_level', '?')}")
    print(f"Confidence        : {synthesis.get('analytical_confidence', 0):.0%}")
    print(f"Critical finding  : {synthesis.get('critical_finding', '')[:120]}")
    print(f"Executive summary : {synthesis.get('executive_summary', '')[:200]}")


if __name__ == "__main__":
    main()
