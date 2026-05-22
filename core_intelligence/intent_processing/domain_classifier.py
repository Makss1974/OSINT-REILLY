#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 1 — Stage 1.2
Domain Classifier — assigns OSINT research domains to the validated query.
Target Directory: /home/ubuntu/IT-PROJECTS/00.Wibe-coding_projects/Wibe_Commander/
Line Length Limit: 100 characters
"""

import json
import logging

from models import ClassificationResult, Domain, DomainScore
from prompts import CLASSIFIER_SYSTEM, CLASSIFIER_USER_TEMPLATE
from core_intelligence.router import ReillyLlmRouter

logger = logging.getLogger(__name__)


class DomainClassifier:
    """
    Stage 1.2 — Класифікує нормалізований запит за 6 OSINT-доменами через ReillyLlmRouter.
    Повертає ClassificationResult з оцінками впевненості та головним доменом.
    """

    def __init__(self, router: ReillyLlmRouter):
        self.router = router

    def classify(self, normalized_query: str) -> ClassificationResult:
        logger.info("[1.2] Classifying query into OSINT domains...")

        user_message = CLASSIFIER_USER_TEMPLATE.format(query=normalized_query)

        # Перемикаємо виклик на наш уніфікований комутатор моделей
        raw_text = self.router.execute_query(
            task_type="default",
            system_prompt=CLASSIFIER_SYSTEM,
            user_prompt=user_message
        )

        raw_text = raw_text.strip()
        logger.debug("[1.2] Raw API response: %s", raw_text)

        data = self._safe_parse(raw_text)
        result = self._build_result(data)

        # Оптимізація виводу логів під ліміт 100 символів
        all_domains_str = [
            f"{d.domain.value}({d.confidence:.2f})" for d in result.domains
        ]
        logger.info(
            "[1.2] ✅ Primary domain: %s | All domains: %s",
            result.primary_domain.value,
            all_domains_str,
        )
        return result

    # ─── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_result(data: dict) -> ClassificationResult:
        raw_domains = data.get("domains", [])
        domain_scores = []

        for item in raw_domains:
            try:
                domain = Domain(item["domain"])
                confidence = float(item.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, confidence))
                domain_scores.append(DomainScore(domain=domain, confidence=confidence))
            except (ValueError, KeyError) as exc:
                logger.warning("[1.2] Skipping unknown domain entry: %s | %s", item, exc)

        if not domain_scores:
            # Надійний фолбек до GENERAL, якщо парсинг повністю збоїть
            domain_scores = [DomainScore(domain=Domain.GENERAL, confidence=0.5)]

        # Сортування результатів за спаданням рівня впевненості
        domain_scores.sort(key=lambda x: x.confidence, reverse=True)

        try:
            primary = Domain(data.get("primary_domain", domain_scores[0].domain.value))
        except ValueError:
            primary = domain_scores[0].domain

        return ClassificationResult(
            domains=domain_scores,
            primary_domain=primary,
            reasoning=data.get("reasoning", ""),
        )

    @staticmethod
    def _safe_parse(text: str) -> dict:
        """Очищає markdown-фенси та безпечно парсить JSON."""
        cleaned = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("[1.2] JSON parse error: %s | raw: %s", exc, text)
            return {
                "domains": [],
                "primary_domain": "GENERAL",
                "reasoning": "Parse error fallback."
            }