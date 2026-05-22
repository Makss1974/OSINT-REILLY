#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 5 — Report Orchestrator
Path: block5_main.py
Line Length Limit: 100 characters

Integration contract:
  INPUT  ← ./state/analytics_result.json  (block4_main.py output)
  OUTPUT → ./reports/<timestamp>_reilly_report.md
"""

import json
import logging
import os
import sys
import argparse
from dotenv import load_dotenv

from core_intelligence.router import ReillyLlmRouter
from core_intelligence.report.report_builder import ReportBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

STATE_DIR             = "./state"
ANALYTICS_RESULT_FILE = os.path.join(STATE_DIR, "analytics_result.json")


def run_block5(analytics_result: dict) -> str:
    """Генерує та зберігає фінальний Markdown-звіт."""
    load_dotenv()

    logger.info("=" * 60)
    logger.info("OSINT-REILLY | Block 5 Report Builder START")
    logger.info("=" * 60)

    router  = ReillyLlmRouter()
    builder = ReportBuilder(router=router)
    report  = builder.build(analytics_result, save=True)

    logger.info("=" * 60)
    logger.info("OSINT-REILLY | Block 5 COMPLETE ✅  |  %d chars", len(report))
    logger.info("=" * 60)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run OSINT-REILLY Block 5 — Report"
    )
    parser.add_argument(
        "analytics_result_file",
        nargs="?",
        default=ANALYTICS_RESULT_FILE,
        help="Path to AnalyticsResult JSON (Block 4 output)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.analytics_result_file):
        logger.critical(
            "AnalyticsResult not found: %s  "
            "Run block4_main.py first.", args.analytics_result_file
        )
        sys.exit(1)

    with open(args.analytics_result_file, "r", encoding="utf-8") as f:
        analytics_result = json.load(f)

    report = run_block5(analytics_result)

    print("\n" + "=" * 60)
    print("BLOCK 5 — REPORT PREVIEW (first 800 chars)")
    print("=" * 60)
    print(report[:800])


if __name__ == "__main__":
    main()
