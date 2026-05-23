#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 1 — MODELS (Спільні моделі даних для конвеєра)
Визначає залізобетонні контракти обміну даними між усіма блоками системи.
Path: /home/ubuntu/IT-PROJECTS/REILLY/block_1_task/models.py
"""

import time
from typing import List, Dict, Any, Optional

class SearchTask:
    """
    Модель окремого завдання на розвідку.
    Використовується Блоком 2 для запуску конкретних бойових колекторів.
    """
    def __init__(
        self,
        task_id: str,
        search_type: str,          # SEMANTIC, SPATIAL_INFRA, TEMPORAL_ANOMALY, LINGUISTIC_STRESS, CORRELATION_CROSS
        bright_data_tool: str,     # SERP_API, Web_Scraper_API
        priority: int,             # Порядок виконання (1 — найвищий)
        initial_queries: List[str], # Масив пошукових лінків або текстових запитів
        meta_instruction: str      # Конкретна інструкція для ШІ чи парсера
    ):
        self.task_id = task_id
        self.search_type = search_type
        self.bright_data_tool = bright_data_tool
        self.priority = priority
        self.initial_queries = initial_queries
        self.meta_instruction = meta_instruction

    def to_dict(self) -> Dict[str, Any]:
        """Конвертація об'єкта в словник для JSON-пакування."""
        return {
            "task_id": self.task_id,
            "search_type": self.search_type,
            "bright_data_tool": self.bright_data_tool,
            "priority": self.priority,
            "initial_queries": self.initial_queries,
            "meta_instruction": self.meta_instruction
        }


class ActionProgram:
    """
    Головний наказ-маніфест, який Блок 1 передає в Блок 2.
    Містить повний структурований план дій та оцінку його стійкості.
    """
    def __init__(
        self,
        query_id: str,
        raw_query: str,
        normalized_query: str,
        target_domains: List[str],
        search_tasks: List[SearchTask],
        plan_robustness: str = "STANDARD" # Заповнюється Адвокатом Диявола (STANDARD / HIGH_VERIFIED)
    ):
        self.query_id = query_id
        self.raw_query = raw_query
        self.normalized_query = normalized_query
        self.target_domains = target_domains
        self.search_tasks = sorted(search_tasks, key=lambda x: x.priority)
        self.plan_robustness = plan_robustness
        self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Повна конвертація всієї програми дій у формат машинного словника."""
        return {
            "query_id": self.query_id,
            "raw_query": self.raw_query,
            "normalized_query": self.normalized_query,
            "target_domains": self.target_domains,
            "plan_robustness": self.plan_robustness,
            "created_at": self.created_at,
            "search_tasks": [task.to_dict() for task in self.search_tasks]
        }


class RejectionReport:
    """
    Модель екстреної зупинки конвеєра.
    Формується, якщо вхідний запит заблоковано контуром безпеки «Субмарина».
    """
    def __init__(self, raw_query: str, rejection_reason: str, stage: str = "1.1_VALIDATION"):
        self.raw_query = raw_query
        self.rejection_reason = rejection_reason
        self.stage = stage
        self.timestamp = time.time()
        self.is_rejected = True

    def to_dict(self) -> Dict[str, Any]:
        """Конвертація звіту про відхилення в словник."""
        return {
            "is_rejected": True,
            "stage": self.stage,
            "raw_query": self.raw_query,
            "rejection_reason": self.rejection_reason,
            "timestamp": self.timestamp
        }