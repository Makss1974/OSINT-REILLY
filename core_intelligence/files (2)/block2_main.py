#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 2 — Data Collection Orchestrator
Path: block2_main.py
Line Length Limit: 100 characters

Coordinates SemanticCollector + InfraCollector based on ActionProgram from Block 1.
Produces a unified CollectionResult for Block 4 (Analytics).

Integration contract:
  INPUT  ← ActionProgram dict  (block1_main.py output)
  OUTPUT → CollectionResult dict saved to ./state/collection_result.json
"""

import json
import logging
import os
import sys
import argparse
from datetime import datetime, timezone
from typing import Union
from dotenv import load_dotenv

from core_intelligence.router import ReillyLlmRouter
from core_intelligence.data_collection.brightdata_client import BrightDataClient
from core_intelligence.data_collection.semantic_collector import SemanticCollector
from core_intelligence.data_collection.infra_collector import InfraCollector

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# State paths
# ─────────────────────────────────────────────────────────────────────────────

STATE_DIR             = "./state"
COLLECTION_RESULT_FILE = os.path.join(STATE_DIR, "collection_result.json")
SEMANTIC_CACHE_DIR    = os.path.join(STATE_DIR, "semantic_cache")
INFRA_CACHE_DIR       = os.path.join(STATE_DIR, "infra_cache")


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_block2(
    action_program: dict,
    country: str = "us",
    language: str = "en",
    country_iso: str = None,
) -> dict:
    """
    Запускає повний конвеєр Блоку 2.

    Args:
        action_program: Словник ActionProgram.to_dict() з виходу Блоку 1.
        country:        Код країни для SERP-запитів (SemanticCollector).
        language:       Мова результатів SERP.
        country_iso:    ISO-код країни вихідного IP для проксі (InfraCollector).

    Returns:
        CollectionResult — об'єднаний результат обох колекторів.
    """
    load_dotenv()
    os.makedirs(STATE_DIR, exist_ok=True)

    raw_query = action_program.get("raw_query", "")

    logger.info("=" * 60)
    logger.info("OSINT-REILLY | Block 2 Pipeline START")
    logger.info("=" * 60)
    logger.info("Query: %.100s", raw_query)

    # ── Ініціалізація спільної інфраструктури ─────────────────────────────────
    try:
        bd_client = BrightDataClient()
    except EnvironmentError as exc:
        logger.critical("BrightDataClient init failed: %s", exc)
        sys.exit(1)

    router = ReillyLlmRouter()

    # ── SemanticCollector: SEMANTIC таски ─────────────────────────────────────
    semantic_result = {}
    semantic_tasks = [
        t for t in action_program.get("search_tasks", [])
        if t.get("search_type") == "SEMANTIC"
    ]
    if semantic_tasks:
        logger.info("[Block2] Starting SemanticCollector (%d tasks)...", len(semantic_tasks))
        collector = SemanticCollector(
            bd_client=bd_client,
            router=router,
            cache_dir=SEMANTIC_CACHE_DIR,
        )
        semantic_result = collector.collect_semantic_pipeline(
            action_program=action_program,
            country=country,
            language=language,
            save_cache=True,
        )
        pairs = len(semantic_result.get("semantic_data", []))
        logger.info("[Block2] SemanticCollector done | dual-sweep pairs: %d", pairs)
    else:
        logger.info("[Block2] No SEMANTIC tasks — SemanticCollector skipped.")

    # ── InfraCollector: SPATIAL_INFRA + QUANTITATIVE таски ───────────────────
    infra_result = {}
    infra_tasks = [
        t for t in action_program.get("search_tasks", [])
        if t.get("search_type") in {"SPATIAL_INFRA", "QUANTITATIVE"}
    ]
    if infra_tasks:
        logger.info("[Block2] Starting InfraCollector (%d tasks)...", len(infra_tasks))
        infra = InfraCollector(bd_client=bd_client, cache_dir=INFRA_CACHE_DIR)
        infra_result = infra.collect_infra_pipeline(
            action_program=action_program,
            zone="residential",
            country_iso=country_iso,
            save_manifest=True,
        )
        stats = infra_result.get("statistics", {})
        logger.info(
            "[Block2] InfraCollector done | HOT=%d | COLD=%d",
            stats.get("hot_signals", 0),
            stats.get("cold_baseline", 0),
        )
    else:
        logger.info("[Block2] No INFRA tasks — InfraCollector skipped.")

    # ── Збираємо єдиний CollectionResult ─────────────────────────────────────
    collection_result = _build_collection_result(
        raw_query, action_program, semantic_result, infra_result
    )

    # Зберігаємо для Block 4
    _save_collection_result(collection_result)

    hot_total  = collection_result["summary"]["hot_infra_signals"]
    sem_pairs  = collection_result["summary"]["semantic_pairs"]
    logger.info("=" * 60)
    logger.info("OSINT-REILLY | Block 2 Pipeline COMPLETE ✅")
    logger.info("Semantic pairs: %d | HOT infra signals: %d", sem_pairs, hot_total)
    logger.info("=" * 60)

    return collection_result


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_collection_result(
    raw_query: str,
    action_program: dict,
    semantic_result: dict,
    infra_result: dict,
) -> dict:
    """Об'єднує результати обох колекторів у єдину структуру для Block 4."""
    sem_pairs  = len(semantic_result.get("semantic_data", []))
    hot_total  = infra_result.get("statistics", {}).get("hot_signals", 0)
    cold_total = infra_result.get("statistics", {}).get("cold_baseline", 0)

    return {
        "raw_query":    raw_query,
        "collected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "primary_domain": action_program.get("primary_domain", "GENERAL"),
        "summary": {
            "semantic_pairs":    sem_pairs,
            "hot_infra_signals": hot_total,
            "cold_infra_signals": cold_total,
            "total_artifacts":   hot_total + cold_total,
        },
        "semantic":   semantic_result,
        "infra":      infra_result,
        "action_program_ref": {
            "estimated_complexity": action_program.get("estimated_complexity", ""),
            "expected_output_type": action_program.get("expected_output_type", ""),
        },
    }


def _save_collection_result(result: dict) -> None:
    """Зберігає CollectionResult у ./state/collection_result.json."""
    try:
        with open(COLLECTION_RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info("[Block2] CollectionResult saved → %s", COLLECTION_RESULT_FILE)
    except OSError as exc:
        logger.error("[Block2] Cannot save CollectionResult: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run OSINT-REILLY Block 2 — Data Collection"
    )
    parser.add_argument(
        "action_program_file",
        nargs="?",
        default="block1_output.json",
        help="Path to ActionProgram JSON file (Block 1 output)",
    )
    parser.add_argument("--country",     default="us",  help="SERP country code")
    parser.add_argument("--language",    default="en",  help="SERP language code")
    parser.add_argument("--country-iso", default=None,  help="Proxy country ISO (e.g. RU)")
    args = parser.parse_args()

    # Завантаження ActionProgram з файлу (вихід Block 1)
    if not os.path.exists(args.action_program_file):
        logger.critical(
            "ActionProgram file not found: %s  "
            "Run block1_main.py first.", args.action_program_file
        )
        sys.exit(1)

    with open(args.action_program_file, "r", encoding="utf-8") as f:
        action_program = json.load(f)

    # Перевірка що це не RejectionReport
    if action_program.get("status") == "REJECTED":
        logger.error(
            "ActionProgram was rejected at Block 1: %s",
            action_program.get("rejection_reason", "")
        )
        sys.exit(1)

    result = run_block2(
        action_program=action_program,
        country=args.country,
        language=args.language,
        country_iso=args.country_iso,
    )

    print("\n" + "=" * 60)
    print("BLOCK 2 OUTPUT SUMMARY")
    print("=" * 60)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
