#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 2 — INFORM PROCESSOR (Головний диспетчер цеху збору)
Оркеструє проходження тасок через 5 рівнів глибини, викликаючи реальні бойові колектори.
Path: /home/ubuntu/IT-PROJECTS/REILLY/block_2_inform/processor.py
"""

import json
import logging
import os
import sys
import time
from enum import Enum
from typing import Dict, Any, List

# Налаштування відносних імпортів для кореня проекту
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core_intelligence.router import ReillyLlmRouter

# Локальні імпорти з підпапки бойових колекторів data_collection/
from .data_collection.brightdata_client import BrightDataClient
from .data_collection.infra_collector import InfraCollector
from .data_collection.semantic_collector import SemanticCollector

logger = logging.getLogger(__name__)

class DataLevel(str, Enum):
    """5 рівнів глибини збору інформації відповідно до нашої Концепції BMW."""
    META        = "L1_META"           # Рівень 1: Мета-дані та контур тасок
    EXTERNAL    = "L2_EXTERNAL"       # Рівень 2: Зовнішній лінгвістичний аналіз
    OPEN        = "L3_OPEN"           # Рівень 3: Відкриті джерела та SERP
    CLOSED      = "L4_CLOSED"         # Рівень 4: Штурм сирої інфраструктури (HTML)
    HUMINT      = "L5_HUMINT"         # Рівень 5: Шар ШІ-експертизи та оцінки ризиків

class InformPackage:
    """Підсумковий пакет зібраних даних, який передається далі в Блок 4 (Аналітика)."""
    def __init__(self, query_id: str, raw_query: str):
        self.query_id = query_id
        self.raw_query = raw_query
        self.collected_at = time.time()
        self.levels_payload: Dict[str, Any] = {}
        self.collection_stats: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Конвертація всього масиву рівнів у словник для JSON-збереження."""
        return {
            "query_id": self.query_id,
            "raw_query": self.raw_query,
            "collected_at": self.collected_at,
            "collection_stats": self.collection_stats,
            "levels_payload": self.levels_payload
        }

class Block2InformProcessor:
    """
    Головний процесор Блоку 2. Проводить ActionProgram через 5 рівнів глибини 
    та інтегрує бойові колектори в єдиний інформаційний пакет.
    """
    def __init__(self, router: ReillyLlmRouter = None):
        self.router = router or ReillyLlmRouter()
        self.bd_client = BrightDataClient()
        
        # Ініціалізація бойових колекторів з передачею шлюзу Bright Data
        self.infra_collector = InfraCollector(self.bd_client)
        self.semantic_collector = SemanticCollector(self.bd_client, self.router)

    def process(self, action_program: Any) -> InformPackage:
        """
        Головний конвеєрний метод обробки.
        Послідовно будує шари L1-L5 інформаційного пакета.
        """
        logger.info("=" * 60)
        logger.info("[Processor] ⚡ БЛОК 2 — INFORM PROCESSOR | Запуск конвеєра збору...")
        logger.info("=" * 60)
        logger.info("Обробка програми дій для ID: %s", action_program.query_id)

        package = InformPackage(action_program.query_id, action_program.normalized_query)

        # ── Рівень L1: META ──────────────────────────────────────────────────
        logger.info("[Processor] 📈 Формування шару Рівня 1 [L1_META]...")
        package.levels_payload[DataLevel.META.value] = {
            "target_domains": action_program.target_domains,
            "plan_robustness": action_program.plan_robustness,
            "total_tasks_received": len(action_program.search_tasks),
            "tasks_manifest": [t.task_id for t in action_program.search_tasks]
        }

        # ── Рівень L3: OPEN (Запуск подвійного семантичного контуру) ───────────
        logger.info("[Processor] 🧠 Формування шару Рівня 3 [L3_OPEN]...")
        semantic_results = self.semantic_collector.collect_semantic_pipeline(action_program)
        package.levels_payload[DataLevel.OPEN.value] = semantic_results

        # ── Рівень L4: CLOSED (Штурм прямої інфраструктури — Демон Максвелла) ──
        logger.info("[Processor] ⚡ Формування шару Рівня 4 [L4_CLOSED]...")
        infra_results = self.infra_collector.collect_infra_pipeline(action_program)
        package.levels_payload[DataLevel.CLOSED.value] = infra_results

        # ── Рівень L2: EXTERNAL (Виділення лінгвістичного стресу) ──────────────
        # Збираємо дані з тасок типу LINGUISTIC_STRESS, які осіли на Рівні 3
        logger.info("[Processor] 📊 Формування шару Рівня 2 [L2_EXTERNAL]...")
        stress_signals = []
        for block in semantic_results.get("semantic_data", []):
            if block.get("search_type") == "LINGUISTIC_STRESS":
                stress_signals.append(block)
        package.levels_payload[DataLevel.EXTERNAL.value] = {
            "stress_raw_signals": stress_signals,
            "extracted_at": time.time()
        }

        # ── Рівень L5: HUMINT (Шар ШІ-оцінки ризиків та викривлень) ───────────
        logger.info("[Processor] 🕵️ Формування аналітичного шару Рівня 5 [L5_HUMINT]...")
        distortion_risk = "LOW"
        verification_available = "HIGH"
        
        # Якщо Демон Максвелла виявив забагато гарячих сигналів, фіксуємо ризик дезінформації
        if infra_results.get("statistics", {}).get("hot_signals", 0) > 2:
            distortion_risk = "MEDIUM_DUE_TO_DYNAMICS"
            
        package.levels_payload[DataLevel.HUMINT.value] = {
            "expert_assessed_at": time.time(),
            "distortion_risk_index": distortion_risk,
            "counter_measures_applied": "DUAL_SWEEP_REDUCTION"
        }

        # 🧮 Розрахунок підсумкової фінальної статистики збору
        total_items = len(stress_signals) + len(infra_results.get("hot_signals_data", [])) + len(semantic_results.get("semantic_data", []))
        package.collection_stats = {
            "status": "COMPLETE",
            "total_items_collected": total_items,
            "distortion_risk": distortion_risk,
            "verification_available": verification_available,
            "cache_paths": {
                "infra": "/home/ubuntu/IT-PROJECTS/REILLY/state/infra_cache",
                "semantic": "/home/ubuntu/IT-PROJECTS/REILLY/state/semantic_cache"
            }
        }

        logger.info("=" * 60)
        logger.info("[Processor] БЛОК 2 — COMPLETE ✅ Зібрано одиниць даних: %d", total_items)
        logger.info("Передаємо InformPackage → БЛОК 4 (АНАЛІТИЧНИЙ ДВИГУН)")
        logger.info("=" * 60)

        return package