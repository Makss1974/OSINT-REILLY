#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 1 — SEARCH TYPE MAPPER (Двоешелонне планування стратегії)
Етап 1.3: Трансформація домену в покрокову стратегію збору від radars до аномалій.
Path: /home/ubuntu/IT-PROJECTS/REILLY/block_1_task/search_type_mapper.py
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SearchTypeMapper:
    """
    Компонент двоешелонного мапування розвідки.
    Перетворює базовий домен знань на складну мережу пошукових тасок.
    """
    def __init__(self, router=None):
        self.router = router

    def map(self, normalized_query: str, domain_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Головний метод побудови плану тасок розвідки.
        Реалізує принцип: Традиційний пошук — це лише паливо для запуску аналізу аномалій.
        """
        logger.info("[Мапувальник] 🛠️ Розрахунок двоешелонної стратегії пошуку...")
        search_tasks = []
        task_counter = 1

        # ─────────────────────────────────────────────────────────────────────
        # ЕШЕЛОН 1: ФУНДАМЕНТ (Традиційний пошук відкритих даних — Радар)
        # ─────────────────────────────────────────────────────────────────────
        base_queries = [normalized_query]
        
        # Додаємо розширені пошукові фрази на основі виділених ключових слів
        if "keywords" in domain_meta and domain_meta["keywords"]:
            extended_kw = " ".join(domain_meta["keywords"][:2])
            base_queries.append(f"{normalized_query} {extended_kw}")

        search_tasks.append({
            "task_id": f"T_{task_counter:02d}",
            "search_type": "SEMANTIC",
            "bright_data_tool": "SERP_API",
            "priority": 1,
            "initial_queries": base_queries,
            "meta_instruction": "Ешелон 1 (Радар): Зібрати первинне коло посилань, згадок та джерел для аналізу."
        })
        task_counter += 1

        # ─────────────────────────────────────────────────────────────────────
        # ЕШЕЛОН 2: ОСНОВНІ КРЕАТИВНІ ТИПИ ПОШУКУ (Глибокі інструменти)
        # ─────────────────────────────────────────────────────────────────────
        
        # 1. Штурм прямої інфраструктури (Твій Демон Максвелла)
        # Якщо класифікатор знайшов URL або домен воєнний/економічний — штурмуємо прямі ресурси
        target_urls = domain_meta.get("target_urls", [])
        if not target_urls and domain_meta.get("domain") in ["MILITARY_SECURITY", "ECONOMIC"]:
            # Якщо користувач не дав лінк, але домен критичний — закладаємо шаблон для майбутнього збору
            target_urls = ["https://custom-target-node.internal"]

        if target_urls:
            search_tasks.append({
                "task_id": f"T_{task_counter:02d}",
                "search_type": "SPATIAL_INFRA",
                "bright_data_tool": "Web_Scraper_API",
                "priority": 2,
                "initial_queries": target_urls,
                "meta_instruction": "Ешелон 2 (Штурм HTML): Завантажити сирий контент прямих вузлів для аналізу дельти змін."
            })
            task_counter += 1

        # 2. УНІКАЛЬНИЙ ТИП: Часові аномалії (TEMPORAL_ANOMALY)
        # Перевірка на те, які дані були видалені або приховані на об'єкті
        if domain_meta.get("domain") in ["MILITARY_SECURITY", "ECONOMIC"]:
            search_tasks.append({
                "task_id": f"T_{task_counter:02d}",
                "search_type": "TEMPORAL_ANOMALY",
                "bright_data_tool": "Web_Scraper_API",
                "initial_queries": target_urls,
                "priority": 3,
                "meta_instruction": "Ешелон 2 (Часовий аудит): Порівняти поточний HTML з архівним бейзлайном. Знайти приховані блоки."
            })
            task_counter += 1

        # 3. УНІКАЛЬНИЙ ТИП: Перехресна кореляція (CORRELATION_CROSS)
        # Автоматично шукаємо підрядників, логістику металу, залізничні колії навколо заводів
        clean_text_lower = normalized_query.lower()
        if any(w in clean_text_lower for w in ["завод", "виробництво", "промисловість"]):
            cross_queries = [
                f"{normalized_query} залізничні маршрути постачання тендер",
                f"{normalized_query} закупівля металу прокат сировина"
            ]
            search_tasks.append({
                "task_id": f"T_{task_counter:02d}",
                "search_type": "CORRELATION_CROSS",
                "bright_data_tool": "SERP_API",
                "priority": 4,
                "initial_queries": cross_queries,
                "meta_instruction": "Ешелон 2 (Кореляція): Розширити контур розвідки на постачальників металу та логістичні вузли."
            })
            task_counter += 1

        # 4. УНІКАЛЬНИЙ ТИП: Лінгвістичний стрес-аналіз (LINGUISTIC_STRESS)
        # Пошук прихованого дефіциту кадрів чи паніки через аналіз тональності вакансій і прес-релізів
        search_tasks.append({
            "task_id": f"T_{task_counter:02d}",
            "search_type": "LINGUISTIC_STRESS",
            "bright_data_tool": "SERP_API",
            "priority": 5,
            "initial_queries": [f"{normalized_query} вакансії терміново дефіцит понаднормово"],
            "meta_instruction": "Ешелон 2 (Маркери стресу): Оцінити наявність лінгвістичних маркерів кризи у текстах підприємств."
        })

        logger.info("[Мапувальник] ✅ План успішно сформовано. Загальна кількість тасок: %d", len(search_tasks))
        return search_tasks