#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 1 — TASK ORCHESTRATOR (Головний диригент цеху планування)
Оркеструє контур: Субмарина → Класифікація → Мапування → Адвокат Диявола → Рефлексія.
Path: /home/ubuntu/IT-PROJECTS/REILLY/block_1_task/orchestrator.py
"""

import os
import sys

# СУВОРO НАЙПЕРШИЙ КРОК: Реєструємо корінь проекту в системних шляхах до будь-яких імпортів
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import json
import logging
import argparse
from typing import Union
from dotenv import load_dotenv

# Абсолютні імпорти з кореня проекту для залізобетонної стабільності конвеєра
from core_intelligence.router import ReillyLlmRouter

# Імпорти внутрішніх модулів Блоку 1 за абсолютними шляхами
from block_1_task.models import ActionProgram, RejectionReport
from block_1_task.task_validator import TaskValidator
from block_1_task.domain_classifier import DomainClassifier
from block_1_task.search_type_mapper import SearchTypeMapper
from block_1_task.action_program_builder import ActionProgramBuilder
from block_1_task.devils_advocate import DevilsAdvocate

logger = logging.getLogger(__name__)

DEMO_QUERY = (
    "Проаналізуй стан оборонної промисловості Росії у 2024 році: "
    "виробничі потужності заводів, динаміку вакансій на ВПК-підприємствах, "
    "тендери на постачання металу та логістику залізничних маршрутів до заводів."
)

def run_block_1_task(raw_query: str, mode: str = "hackathon") -> Union[ActionProgram, RejectionReport]:
    """
    Головна funktion запуска Блоку 1. 
    Оркеструє роботу всіх підмодулів цеху та реалізує контур рефлексії.
    """
    load_dotenv()
    router = ReillyLlmRouter()

    logger.info("=" * 60)
    logger.info("BLOCK 1 — TASK | Pipeline START [%s]", mode.upper())
    logger.info("=" * 60)
    logger.info("Вхідна аналітична ціль: %.120s", raw_query)

    # ── Етап 1.1: Субмарина (Валідація та нормалізація) ───────────────────────────
    validator = TaskValidator(router)
    validation = validator.validate(raw_query)

    if not validation.is_approved():
        report = RejectionReport(
            raw_query=raw_query,
            rejection_reason=validation.reason or "Невідома помилка валідації",
            stage="1.1_VALIDATION",
        )
        logger.warning("[Orchestrator] Конвеєр зупинено «Субмариною» на Етапі 1.1.")
        return report

    # ── Етап 1.2: Класифікація за онтологічними доменами знань ───────────────────
    classifier = DomainClassifier(router)
    classification = classifier.classify(validation.normalized_query)

    # ── Етап 1.3: Двоешелонне мапування стратегії пошуку (Радар → Аномалії) ──────
    mapper = SearchTypeMapper(router)
    search_plan_raw = mapper.map(validation.normalized_query, classification)

    # ── Етап 1.4: Первинна інженерна збірка програми дій ────────────────────────
    builder = ActionProgramBuilder(router)
    action_program = builder.build(validation, classification, search_plan_raw)

    # ── Етап 1.5: КОНТУР РЕФЛЕКСІЇ (Стрес-тест Адвоката Диявола) ──────────────────
    advocate = DevilsAdvocate(router)
    vulnerabilities = advocate.audit_plan(validation.normalized_query, action_program)

    if vulnerabilities:
        logger.warning("[Orchestrator] ⚠️ Виявлено %d прогалин. Запуск циклу оптимізації...", len(vulnerabilities))
        # Перебудовуємо і загартовуємо таски на основі зауважень критичного контуру
        action_program = builder.rebuild_with_critic(
            current_program=action_program,
            vulnerabilities=vulnerabilities
        )
    else:
        logger.info("[Orchestrator] ✅ Первинний plan визнано стійким з першого проходу.")

    logger.info("=" * 60)
    logger.info("BLOCK 1 — TASK | Pipeline COMPLETE ✅")
    logger.info("Передаємо ActionProgram %s → БЛОК 2 (ЗБІР ДАНИХ)", action_program.query_id)
    logger.info("=" * 60)

    return action_program

def main() -> None:
    """Точка входу для автономного CLI-запуску та тестування Блоку 1."""
    parser = argparse.ArgumentParser(description="OSINT-REILLY | BLOCK 1 — TASK Pipeline")
    parser.add_argument("query", nargs="?", default=DEMO_QUERY, help="Запит на дослідження")
    parser.add_argument(
        "--mode",
        choices=["hackathon", "full-tank", "private"],
        default="hackathon",
        help="Профіль запуску системи"
    )
    args = parser.parse_args()

    result = run_block_1_task(args.query, args.mode)

    print("\n" + "=" * 60)
    print("BLOCK 1 — TASK | ENGINE OUTPUT")
    print("=" * 60)

    output_dict = result.to_dict()
    output_json = json.dumps(output_dict, ensure_ascii=False, indent=2)
    print(output_json)

    # Логіка стабільного збереження результатів за профілями (ТЗ)
    if args.mode == "full-tank":
        output_path = "/home/ubuntu/IT-PROJECTS/REILLY/state/block1_history.lsonl"
    elif args.mode == "private":
        output_path = "/home/ubuntu/IT-PROJECTS/REILLY/state/reports/private/block1_task_output.json"
    else:
        output_path = "block1_task_output.json"

    os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None
    
    if args.mode == "full-tank":
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(output_dict, ensure_ascii=False) + "\n")
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        
    logger.info("Результати цеху успішно зафіксовані в контурі: %s", output_path)

if __name__ == "__main__":
    main()