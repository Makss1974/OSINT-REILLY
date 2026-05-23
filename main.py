#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | MAIN — ГОЛОВНИЙ ОРКЕСТРАТОР СИСТЕМИ (БЛОК 0)
Path: main.py
Line Length Limit: 100 characters

Main orchestrator of the entire engine execution pipeline. Manages global lifecycle.
"""

import os
import sys

# КРОК 1: Залізобетонно реєструємо корінь ДО того, як завантажиться хоч один наш модуль
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import logging
import time
import argparse
from datetime import datetime

# КРОК 2: Імпортуємо оркестратори та інфраструктурний менеджер сховища
from core_intelligence.data_storage.storage_manager import StorageManager
from block_1_task.orchestrator import run_block_1_task
from block_2_inform.processor import Block2InformProcessor
from block_4_analytics.analytics_engine import Block4AnalyticsEngine
from block_5_report.report_builder import Block5ReportBuilder, ReportFormat

# Налаштування логів системи
LOG_DIR = os.path.join(CURRENT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | [MAIN_CORE] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "reilly_core.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

DEFAULT_QUERY = (
    "Проаналізуй стан оборонної промисловості Росії у 2024 році: "
    "виробничі потужності заводів, динаміку вакансій на ВПК-підприємствах, "
    "тендери на постачання металу та логістику залізничних маршрутів до заводів."
)


def execute_reilly_engine(query: str, mode: str = "hackathon") -> str:
    """Глобальний конвеєр запуску та оркестрації всіх блоків системи OSINT-REILLY."""
    start_time = time.time()
    logger.info("=" * 70)
    logger.info("🛡️  OSINT-REILLY ENGINE CORE v4.2 | ЗАПУСК ГОЛОВНОГО КОНВЕЄРА")
    logger.info("=" * 70)

    # Ініціалізуємо єдине інфраструктурне ядро сховища даних
    storage_mgr = StorageManager(base_state_dir=os.path.join(CURRENT_DIR, "state"))

    # БЛОК 1: Валідація, класифікація та генерація програми дій
    action_program = run_block_1_task(query, mode=mode)

    if hasattr(action_program, "is_rejected") and action_program.is_rejected:
        logger.warning("[MAIN] ⚠️ Конвеєр зупинено Блоком 1: %s", action_program.rejection_reason)
        return "CONVEYOR_REJECTED"

    # БЛОК 2: Збір інформації через 5 рівнів BMW (передаємо спільне ядро сховища)
    inform_processor = Block2InformProcessor(storage_mgr=storage_mgr)
    inform_package = inform_processor.process(action_program)

    # БЛОК 4: Аналітичний двигун (Матриця оцінки сигналів)
    analytics_engine = Block4AnalyticsEngine()
    analytics_result = analytics_engine.analyze(inform_package)

    # БЛОК 5: Конструктор фінальних паспортів та звітів
    report_builder = Block5ReportBuilder()
    generated_report = report_builder.build(analytics_result)

    # Визначення цільової директорії для виводу залежно від режиму
    output_dir_map = {
        "hackathon": os.path.join(CURRENT_DIR, "state", "reports"),
        "full-tank": os.path.join(CURRENT_DIR, "state", "reports", "defense"),
        "private":   os.path.join(CURRENT_DIR, "state", "reports", "private")
    }
    target_dir = output_dir_map.get(mode, os.path.join(CURRENT_DIR, "state", "reports"))

    # Збереження результатів на диск у трьох бойових форматах
    report_builder.save_report_to_disk(generated_report, ReportFormat.JSON, target_dir)
    report_builder.save_report_to_disk(generated_report, ReportFormat.HTML, target_dir)
    final_md_path = report_builder.save_report_to_disk(
        generated_report, ReportFormat.MARKDOWN, target_dir
    )

    elapsed_time = time.time() - start_time
    logger.info("=" * 70)
    logger.info("✅ OSINT-REILLY ENGINE PIPELINE COMPLETE SUCCESS")
    logger.info("🔑 ID Запиту: %s | Час обробки: %.2f сек", generated_report.query_id, elapsed_time)
    logger.info("=" * 70)

    return final_md_path


def main() -> None:
    """Точка входу CLI."""
    parser = argparse.ArgumentParser(description="OSINT-REILLY Engine Main Orchestrator")
    parser.add_argument("query", nargs="?", default=DEFAULT_QUERY, help="Аналітичний запит")
    parser.add_argument("--mode", choices=["hackathon", "full-tank", "private"], default="hackathon")
    args = parser.parse_args()
    execute_reilly_engine(args.query, args.mode)


if __name__ == "__main__":
    main()