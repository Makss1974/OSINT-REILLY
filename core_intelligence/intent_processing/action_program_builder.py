#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 1 — Stage 1.4
Action Program Builder — synthesises the final ActionProgram JSON
passed to Block 2, Block 3, and Block 4.
Target Directory: /home/ubuntu/IT-PROJECTS/00.Wibe-coding_projects/Wibe_Commander/
Line Length Limit: 100 characters
"""

import json
import logging

from models import (
    ValidationResult,
    ClassificationResult,
    SearchPlan,
    ActionProgram,
    Complexity,
    Domain,
    SearchType,
)
from prompts import ACTION_BUILDER_SYSTEM, ACTION_BUILDER_USER_TEMPLATE
from core_intelligence.router import ReillyLlmRouter

logger = logging.getLogger(__name__)

# Домени, які автоматично піднімають рівень складності до CRITICAL
CRITICAL_DOMAINS = {Domain.MILITARY_SECURITY}

# Домени, які впливають на присвоєння статусу HIGH
HIGH_DOMAINS = {Domain.MILITARY_SECURITY, Domain.SOCIO_POLITICAL}

# Важкі типи пошуку, що вимагають камуфляжу та підняття рівня складності
HEAVY_SEARCH_TYPES = {SearchType.SOCIAL_LISTENING, SearchType.SPATIAL_INFRA}


class ActionProgramBuilder:
    """
    Stage 1.4 — Об'єднує результати етапів 1.1–1.3 у фінальну структуру ActionProgram.
    Використовує ReillyLlmRouter для текстових приміток, але застосовує жорсткі
    детерміновані правила валідації рівня складності перед затвердженням програми.
    """

    def __init__(self, router: ReillyLlmRouter):
        self.router = router

    def build(
        self,
        validation: ValidationResult,
        classification: ClassificationResult,
        search_plan: SearchPlan,
    ) -> ActionProgram:
        logger.info("[1.4] Building final Action Program...")

        # ── Детермінований математичний розрахунок складності за правилами ─────
        complexity = self._calculate_complexity(classification, search_plan)

        # ── Запит до роутера моделей для збору приміток та метаданих ───────────
        search_types_used = list({t.search_type.value for t in search_plan.search_tasks})
        domains_json = json.dumps(classification.to_dict(), ensure_ascii=False)

        user_message = ACTION_BUILDER_USER_TEMPLATE.format(
            normalized_query=validation.normalized_query,
            primary_domain=classification.primary_domain.value,
            domains_json=domains_json,
            tasks_count=len(search_plan.search_tasks),
            search_types=", ".join(search_types_used),
        )

        raw_text = self.router.execute_query(
            task_type="default",
            system_prompt=ACTION_BUILDER_SYSTEM,
            user_prompt=user_message
        )

        raw_text = raw_text.strip()
        logger.debug("[1.4] Raw API response: %s", raw_text)

        meta = self._safe_parse(raw_text)

        # Hard-rules guard: правила коду перевищують пропозицію ШІ, якщо ШІ занизив ризики
        ai_complexity_str = meta.get("estimated_complexity", complexity.value)
        ai_complexity = self._parse_complexity(ai_complexity_str)
        final_complexity = self._max_complexity(complexity, ai_complexity)

        program = ActionProgram(
            raw_query=validation.normalized_query or "",
            normalized_query=validation.normalized_query or "",
            primary_domain=classification.primary_domain,
            all_domains=classification.domains,
            search_tasks=search_plan.search_tasks,
            estimated_complexity=final_complexity,
            expected_output_type=meta.get(
                "expected_output_type", "Analytical intelligence report"
            ),
            notes=meta.get("notes", ""),
        )

        logger.info(
            "[1.4] ✅ ActionProgram ready | complexity: %s | tasks: %d",
            final_complexity.value,
            len(program.search_tasks),
        )
        return program

    # ─── complexity logic ──────────────────────────────────────────────────────

    @staticmethod
    def _calculate_complexity(
        classification: ClassificationResult,
        search_plan: SearchPlan,
    ) -> Complexity:
        active_domains = {ds.domain for ds in classification.domains}
        active_search_types = {t.search_type for t in search_plan.search_tasks}

        # CRITICAL: військовий контур + 3 або більше активних типів пошуку
        if CRITICAL_DOMAINS & active_domains and len(active_search_types) >= 3:
            return Complexity.CRITICAL

        # HIGH: наявність воєнних/політичних ризиків АБО підключення важких скраперів
        if (HIGH_DOMAINS & active_domains) or (HEAVY_SEARCH_TYPES & active_search_types):
            return Complexity.HIGH

        # MEDIUM: 2+ активних домени або 2+ паралельних типи пошуку даних
        if len(active_domains) >= 2 or len(active_search_types) >= 2:
            return Complexity.MEDIUM

        return Complexity.LOW

    @staticmethod
    def _parse_complexity(value: str) -> Complexity:
        try:
            return Complexity(value.upper())
        except ValueError:
            return Complexity.MEDIUM

    @staticmethod
    def _max_complexity(a: Complexity, b: Complexity) -> Complexity:
        """Повертає найвищий рівень складності з двох переданих варіантів."""
        order = [Complexity.LOW, Complexity.MEDIUM, Complexity.HIGH, Complexity.CRITICAL]
        return order[max(order.index(a), order.index(b))]

    @staticmethod
    def _safe_parse(text: str) -> dict:
        """Очищає markdown фенси та безпечно утилізує збої парсингу через фолбек."""
        cleaned = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("[1.4] JSON parse error: %s | raw: %s", exc, text)
            return {
                "estimated_complexity": "MEDIUM",
                "expected_output_type": "Analytical intelligence report",
                "notes": "Metadata parse error — defaults applied.",
            }