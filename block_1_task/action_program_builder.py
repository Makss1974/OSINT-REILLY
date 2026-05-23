#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 1 — ACTION PROGRAM BUILDER (Збирач та Оптимізатор плану)
Етап 1.4: Формування фінального машинного маніфесту та його динамічна рефлексія.
Path: /home/ubuntu/IT-PROJECTS/REILLY/block_1_task/action_program_builder.py
"""

import logging
import hashlib
import time
from typing import List, Dict, Any
from core_intelligence.router import ReillyLlmRouter
from .models import SearchTask, ActionProgram

logger = logging.getLogger(__name__)

class ActionProgramBuilder:
    """
    Компонент інженерної збірки програми дій.
    Вміє пакувати первинні плани та динамічно виправляти їх на основі логічної критики.
    """
    def __init__(self, router: ReillyLlmRouter):
        self.router = router

    def build(self, validation: Any, classification: Dict[str, Any], search_plan_raw: List[Dict[str, Any]]) -> ActionProgram:
        """
        Первинна збірка маніфесту програми дій з масиву сирих словників-тасок.
        """
        logger.info("[Builder] 🏗️ Початок первинної збірки ActionProgram...")
        
        # Генеруємо унікальний ID запиту на основі тимчасової мітки та тексту
        salt = f"{time.time()}-{validation.normalized_query}"
        query_id = f"REQ_{hashlib.sha1(salt.encode('utf-8')).hexdigest()[:10].upper()}"

        search_tasks = []
        for raw_task in search_plan_raw:
            task = SearchTask(
                task_id=raw_task["task_id"],
                search_type=raw_task["search_type"],
                bright_data_tool=raw_task["bright_data_tool"],
                priority=raw_task["priority"],
                initial_queries=raw_task["initial_queries"],
                meta_instruction=raw_task["meta_instruction"]
            )
            search_tasks.append(task)

        program = ActionProgram(
            query_id=query_id,
            raw_query=validation.normalized_query, # Фіксуємо вже чисте ядро
            normalized_query=validation.normalized_query,
            target_domains=[classification.get("domain", "GENERAL")],
            search_tasks=search_tasks,
            plan_robustness="STANDARD"
        )
        
        logger.info("[Builder] Первинний маніфест %s успішно зібрано. Усього тасок: %d", query_id, len(search_tasks))
        return program

    def rebuild_with_critic(self, current_program: ActionProgram, vulnerabilities: List[Dict[str, str]]) -> ActionProgram:
        """
        УНІКАЛЬНИЙ КОНТУР РЕФЛЕКСІЇ:
        Перебудова та посилення плану дій на основі знайдених Адвокатом Диявола дірок.
        """
        logger.info("[Builder] 🔄 Модифікація плану дій під впливом логічної критики...")
        
        # Аналізуємо типи знайдених критиком помилок
        v_types = [v["type"] for v in vulnerabilities]

        # Кейс 1: Критик виявив однобокість плану (BIAS_RISK)
        # Додаємо примусові контер-запити в існуючі семантичні таски
        if "BIAS_RISK" in v_types:
            logger.info("[Builder] Оптимізація: Впровадження дзеркальних контурів проти упередженості.")
            for task in current_program.search_tasks:
                if task.search_type == "SEMANTIC":
                    task.meta_instruction += " ПРИМУСОВО: додати збір протилежних аргументів, критики та спростувань фактів."
                    # Подвоюємо вибірку — додаємо дзеркальний запит з часткою НЕ або "криза"
                    extended_queries = []
                    for q in task.initial_queries:
                        extended_queries.append(q)
                        extended_queries.append(f"{q} проблеми аномалії дефіцит спростування")
                    task.initial_queries = list(set(extended_queries))

        # Кейс 2: Забагато шуму в SERP (OVER-RELIANCE_ON_SEARCH)
        # Знижуємо пріоритет або робимо інструкцію жорсткішою — вимагати тільки офіційні PDF/документи
        if "OVER-RELIANCE_ON_SEARCH" in v_types:
            logger.info("[Builder] Оптимізація: Посилення фільтрації пошукового шуму.")
            for task in current_program.search_tasks:
                if task.bright_data_tool == "SERP_API":
                    task.meta_instruction += " СУВОРО: Ігнорувати новинний шум та блоги. Шукати тільки прямі лінки на тендери, PDF-документи, звіти та офіційні реєстри."

        # Кейс 3: ШІ знайшов приховану критичну прогалину в логіці (AI_CRITICAL_GAP)
        # Створюємо нову, додаткову сувору таску найвищого пріоритету
        if "AI_CRITICAL_GAP" in v_types:
            logger.info("[Builder] Оптимізація: Додавання екстреної таски виправлення прогалин аналізу.")
            # Зсуваємо всі пріоритети на 1 крок назад, звільняючи місце для Critical Task
            for task in current_program.search_tasks:
                task.priority += 1
                
            critical_task = SearchTask(
                task_id="T_CRIT",
                search_type="CORRELATION_CROSS",
                bright_data_tool="SERP_API",
                priority=1, # Найвищий пріоритет
                initial_queries=[f"{current_program.normalized_query} структура управління власники підрядники"],
                meta_instruction="ЕКСТРЕНА ТАСКА КРИТИКА: Провести глибокий пошук зв'язків першої особи об'єкта, прихованих холдингів та афілійованих структур."
            )
            current_program.search_tasks.append(critical_task)

        # Пересортовуємо таски за оновленими пріоритетами
        current_program.search_tasks = sorted(current_program.search_tasks, key=lambda x: x.priority)
        current_program.plan_robustness = "HIGH_VERIFIED"
        
        logger.info("[Builder] ✅ План успішно загартовано. Нова кількість тасок: %d", len(current_program.search_tasks))
        return current_program