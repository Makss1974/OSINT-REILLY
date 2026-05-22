#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 1 — Stage 1.1
Task Validator — «Submarine Filter»
Validates incoming queries for technical reachability and ethical compliance.
Target Directory: /home/ubuntu/IT-PROJECTS/00.Wibe-coding_projects/Wibe_Commander/
Line Length Limit: 100 characters
"""

import json
import logging

from models import ValidationResult, ValidationStatus
from prompts import VALIDATOR_SYSTEM, VALIDATOR_USER_TEMPLATE
from core_intelligence.router import ReillyLlmRouter

logger = logging.getLogger(__name__)


class TaskValidator:
    """
    Stage 1.1 — Валідує сирий запит користувача через уніфікований ReillyLlmRouter.
    Повертає ValidationResult: APPROVED (з нормалізованим текстом) або REJECTION (з причиною).
    """

    def __init__(self, router: ReillyLlmRouter):
        self.router = router

    def validate(self, raw_query: str) -> ValidationResult:
        logger.info("[1.1] Validating query: %.80s...", raw_query)

        user_message = VALIDATOR_USER_TEMPLATE.format(query=raw_query)

        # Викликаємо наш уніфікований роутер замість прямого Anthropic клієнта
        raw_text = self.router.execute_query(
            task_type="default",
            system_prompt=VALIDATOR_SYSTEM,
            user_prompt=user_message
        )
        
        raw_text = raw_text.strip()
        logger.debug("[1.1] Raw API response: %s", raw_text)

        data = self._safe_parse(raw_text)

        status = ValidationStatus(data.get("status", "REJECTION"))
        reason = data.get("reason")
        normalized = data.get("normalized_query")

        result = ValidationResult(
            status=status,
            reason=reason,
            normalized_query=normalized,
        )

        if result.is_approved():
            logger.info("[1.1] ✅ APPROVED — normalized query ready.")
        else:
            logger.warning("[1.1] ❌ REJECTED — reason: %s", reason)

        return result

    # ─── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_parse(text: str) -> dict:
        """Очищає markdown-теги ```json якщо вони присутні, та парсить JSON."""
        cleaned = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("[1.1] JSON parse error: %s | raw: %s", exc, text)
            # Fail-safe: у разі збою маркуємо як REJECTION, щоб уникнути пропуску сміття
            return {
                "status": "REJECTION",
                "reason": f"Validator parse error: {exc}",
                "normalized_query": None,
            }