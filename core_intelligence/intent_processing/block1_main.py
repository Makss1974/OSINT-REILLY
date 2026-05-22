#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 1 — Orchestrator
Runs the full Stage 1.1 → 1.2 → 1.3 → 1.4 pipeline using unified ReillyLlmRouter.
Target Directory: /home/ubuntu/IT-PROJECTS/00.Wibe-coding_projects/Wibe_Commander/
Line Length Limit: 100 characters
"""

import json
import logging
import os
import sys
import argparse
from typing import Union
from dotenv import load_dotenv

from models import ActionProgram, RejectionReport
from task_validator import TaskValidator
from domain_classifier import DomainClassifier
from search_type_mapper import SearchTypeMapper
from action_program_builder import ActionProgramBuilder
from core_intelligence.router import ReillyLlmRouter

# ─────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Demo query
# ─────────────────────────────────────────────

DEMO_QUERY = (
    "Проаналізуй стан оборонної промисловості Росії у 2024 році: "
    "виробничі потужності заводів, динаміку вакансій на ВПК-підприємствах, "
    "тендери на постачання металу та логістику залізничних маршрутів до заводів."
)


# ─────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────

def run_block1(raw_query: str, mode: str = "hackathon") -> Union[ActionProgram, RejectionReport]:
    """
    Запускає повний конвеєр Блоку 1 через уніфікований інтерфейс моделей ШІ.
    """
    load_dotenv()
    
    # Ініціалізація єдиного комутатора мізків системи
    router = ReillyLlmRouter()

    logger.info("=" * 60)
    logger.info("OSINT-REILLY | Block 1 Pipeline START [%s]", mode.upper())
    logger.info("=" * 60)
    logger.info("Input query (first 120 chars): %.120s", raw_query)

    # ── Stage 1.1: Validation (Фільтр «Субмарини») ────────────────────────────
    validator = TaskValidator(router)
    validation = validator.validate(raw_query)

    if not validation.is_approved():
        report = RejectionReport(
            raw_query=raw_query,
            rejection_reason=validation.reason or "Unknown validation failure",
            stage="1.1_VALIDATION",
        )
        logger.warning("Pipeline terminated at Stage 1.1.")
        return report

    # ── Stage 1.2: Domain classification ─────────────────────────────────────
    classifier = DomainClassifier(router)
    classification = classifier.classify(validation.normalized_query)

    # ── Stage 1.3: Search type mapping ───────────────────────────────────────
    mapper = SearchTypeMapper(router)
    search_plan = mapper.map(validation.normalized_query, classification)

    # ── Stage 1.4: Action program assembly ───────────────────────────────────
    builder = ActionProgramBuilder(router)
    action_program = builder.build(validation, classification, search_plan)

    logger.info("=" * 60)
    logger.info("OSINT-REILLY | Block 1 Pipeline COMPLETE ✅")
    logger.info("=" * 60)

    return action_program


# ─────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Run OSINT-REILLY Block 1 Pipeline")
    parser.add_argument("query", nargs="?", default=DEMO_QUERY, help="Research target query")
    parser.add_argument(
        "--mode",
        choices=["hackathon", "full-tank", "private"],
        default="hackathon",
        help="System execution profile mode"
    )
    args = parser.parse_args()

    result = run_block1(args.query, args.mode)

    print("\n" + "=" * 60)
    print("BLOCK 1 OUTPUT")
    print("=" * 60)

    output_dict = result.to_dict()
    output_json = json.dumps(output_dict, ensure_ascii=False, indent=2)
    print(output_json)

    # Диференціація збереження даних відповідно до задекларованих комерційних основ
    if args.mode == "full-tank":
        # Важкий оборонний контур: дозапис одним рядком в аналітичну історію .lsonl
        lsonl_path = "/home/ubuntu/KUCOIN_PROD/bots/bot_1/state/trades_history.lsonl"
        os.makedirs(os.path.dirname(lsonl_path), exist_ok=True)
        single_line_payload = json.dumps(output_dict, ensure_ascii=False)
        with open(lsonl_path, "a", encoding="utf-8") as f:
            f.write(single_line_payload + "\n")
        logger.info("Analytical log successfully appended to LSONL: %s", lsonl_path)
        
    elif args.mode == "private":
        # Особистий контур адміністратора: тиха доставка звіту в закриту папку репортів
        report_dir = "/home/ubuntu/01.KUCOIN_PROD/direct/analysis/reports"
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, "block1_private_program.json")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        logger.info("Private report silently saved to: %s", report_path)
        
    else:
        # Стандартний режим для хакатону: збереження локального json-файлу для GUI
        output_path = "block1_output.json"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        logger.info("Output saved to %s", output_path)


if __name__ == "__main__":
    main()