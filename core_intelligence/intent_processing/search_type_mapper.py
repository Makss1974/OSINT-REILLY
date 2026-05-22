#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 1 — Stage 1.3
Search Type Mapper — maps domains to Bright Data tools and generates initial queries.
Target Directory: /home/ubuntu/IT-PROJECTS/00.Wibe-coding_projects/Wibe_Commander/
Line Length Limit: 100 characters
"""

import json
import logging

from models import (
    ClassificationResult,
    SearchPlan,
    SearchTask,
    SearchType,
    BrightDataTool,
    Domain,
)
from prompts import SEARCH_MAPPER_SYSTEM, SEARCH_MAPPER_USER_TEMPLATE
from core_intelligence.router import ReillyLlmRouter

logger = logging.getLogger(__name__)

# Канонічна карта інструментів — ніколи не змінюється, незалежно від галюцинацій ШІ
TOOL_MAP: dict[SearchType, BrightDataTool] = {
    SearchType.QUANTITATIVE:     BrightDataTool.WEB_SCRAPER_API,
    SearchType.SEMANTIC:         BrightDataTool.SERP_API,
    SearchType.SOCIAL_LISTENING: BrightDataTool.SCRAPING_BROWSER,
    SearchType.SPATIAL_INFRA:    BrightDataTool.WEB_UNLOCKER,
}


class SearchTypeMapper:
    """
    Stage 1.3 — Визначає необхідні типи пошуку, призначає інструменти Bright Data
    та генерує первинні ключові слова/dorks для кожного завдання.
    """

    def __init__(self, router: ReillyLlmRouter):
        self.router = router

    def map(
        self,
        normalized_query: str,
        classification: ClassificationResult,
    ) -> SearchPlan:
        logger.info("[1.3] Mapping search types and generating initial queries...")

        classification_json = json.dumps(
            classification.to_dict(), ensure_ascii=False, indent=2
        )

        user_message = SEARCH_MAPPER_USER_TEMPLATE.format(
            query=normalized_query,
            classification_json=classification_json,
        )

        # Виклик нашого уніфікованого комутатора моделей
        raw_text = self.router.execute_query(
            task_type="default",
            system_prompt=SEARCH_MAPPER_SYSTEM,
            user_prompt=user_message
        )

        raw_text = raw_text.strip()
        logger.debug("[1.3] Raw API response: %s", raw_text)

        data = self._safe_parse(raw_text)
        plan = self._build_plan(data, classification)

        logger.info(
            "[1.3] ✅ Search plan ready: %d tasks | types: %s",
            len(plan.search_tasks),
            [t.search_type.value for t in plan.search_tasks],
        )
        return plan

    # ─── helpers ──────────────────────────────────────────────────────────────

    def _build_plan(self, data: dict, classification: ClassificationResult) -> SearchPlan:
        raw_tasks = data.get("search_tasks", [])
        tasks: list[SearchTask] = []

        for item in raw_tasks:
            try:
                search_type = SearchType(item["search_type"])
                # Жорстке застосування канонічного мапування інструментів Bright Data
                bright_data_tool = TOOL_MAP[search_type]

                target_domains: list[Domain] = []
                for d in item.get("target_domains", []):
                    try:
                        target_domains.append(Domain(d))
                    except ValueError:
                        pass

                tasks.append(
                    SearchTask(
                        search_type=search_type,
                        bright_data_tool=bright_data_tool,
                        priority=int(item.get("priority", 99)),
                        initial_queries=item.get("initial_queries", []),
                        target_domains=target_domains,
                    )
                )
            except (ValueError, KeyError) as exc:
                logger.warning("[1.3] Skipping invalid search task: %s | %s", item, exc)

        # Сортування завдань збору за пріоритетом (від меншого до більшого)
        tasks.sort(key=lambda x: x.priority)

        # Фолбек: якщо з якихось причин ШІ віддав пустий список, вмикаємо базовий SEMANTIC збір
        if not tasks:
            logger.warning("[1.3] No valid tasks parsed — applying SEMANTIC fallback.")
            tasks.append(
                SearchTask(
                    search_type=SearchType.SEMANTIC,
                    bright_data_tool=TOOL_MAP[SearchType.SEMANTIC],
                    priority=1,
                    initial_queries=[classification.primary_domain.value + " analysis"],
                    target_domains=[classification.primary_domain],
                )
            )

        return SearchPlan(search_tasks=tasks)

    @staticmethod
    def _safe_parse(text: str) -> dict:
        """Видаляє markdown-теги та безпечно перетворює текст на словник."""
        cleaned = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("[1.3] JSON parse error: %s | raw: %s", exc, text)
            return {"search_tasks": []}