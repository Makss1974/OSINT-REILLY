#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 1 — TASK VALIDATOR (Контур захисту «Субмарина»)
Етап 1.1: Первинна валідація, відсікання аномальних запитів та нормалізація тексту.
Path: /home/ubuntu/IT-PROJECTS/REILLY/block_1_task/task_validator.py
"""

import logging
from typing import Optional
from core_intelligence.router import ReillyLlmRouter

logger = logging.getLogger(__name__)

class ValidationResult:
    """Об'єкт результату валідації, що передається по ланцюжку конвеєра."""
    def __init__(self, approved: bool, reason: Optional[str] = None, normalized_query: Optional[str] = None):
        self.approved = approved
        self.reason = reason
        self.normalized_query = normalized_query

    def is_approved(self) -> bool:
        """Перевірка, чи дозволено запуск конвеєра далі."""
        return self.approved


class TaskValidator:
    """
    Компонент «Субмарина». Забезпечує вхідний контроль якості,
    захищає систему від галюцинацій та шкідливих вхідних конструкцій.
    """
    def __init__(self, router: ReillyLlmRouter):
        self.router = router

    def validate(self, raw_query: str) -> ValidationResult:
        """
        Головний метод валідації.
        Перевіряє сирий текст запиту за жорсткими правилами.
        """
        logger.info("[Субмарина] ⚓ Запуск первинного контуру валідації запиту...")

        # 1. Захист від порожніх або ультра-коротких конструкцій
        clean_query = raw_query.strip() if raw_query else ""
        if not clean_query or len(clean_query) < 15:
            logger.warning("[Субмарина] ❌ Запит занадто короткий або порожній.")
            return ValidationResult(
                approved=False,
                reason="Вхідний запит занадто короткий (мінімум 15 символів для аналізу)."
            )

        # 2. Фільтр безпеки та деструктивних інструкцій (Промпт-ін'єкції)
        # Блокуємо спроби змусити ШІ вийти за контури OSINT-завдань
        lower_query = clean_query.lower()
        forbidden_markers = ["ignore previous instructions", "forget everything", "ignore rules", "ти маніпулятор"]
        if any(marker in lower_query for marker in forbidden_markers):
            logger.warning("[Субмарина] ❌ Виявлено спробу промпт-ін'єкції!")
            return ValidationResult(
                approved=False,
                reason="Запит відхилено системним фільтром: виявлено деструктивні інструкції."
            )

        # 3. Виклик ШІ-маршрутизатора для нормалізації тексту та стиснення смислів
        # Замість хаотичного користувацького тексту робимо чітке OSINT-формулювання
        try:
            logger.info("[Субмарина] Виклик ШІ-роутера для побудови нормалізованого ядра запиту...")
            
            # Формуємо закритий промпт для ШІ-роутера
            normalization_prompt = (
                f"Очисти та нормалізуй цей OSINT-запит. Виділи сухий аналітичний зміст, "
                f"прибери емоції, залиш ключові об'єкти, локації та часові рамки.\n"
                f"Сирий запит: {clean_query}"
            )
            
            normalized = self.router.execute_normalization(normalization_prompt)
            
            if not normalized or len(normalized.strip()) < 10:
                logger.error("[Субмарина] ШІ повернув порожню або некоректну нормалізацію.")
                return ValidationResult(
                    approved=False,
                    reason="Помилка штучного інтелекту при спробі нормалізації аналітичного ядра."
                )

            logger.info("[Субмарина] ✅ Запит успішно схвалено та нормалізовано.")
            return ValidationResult(
                approved=True,
                normalized_query=normalized.strip()
            )

        except Exception as e:
            logger.error("[Субмарина] 💥 Критична помилка під час комунікації з роутером: %s", str(e))
            # У разі падіння API ШІ на хакатоні, використовуємо сирий запит як резервний бейзлайн (fallback)
            logger.warning("[Субмарина] Активовано резервний контур безпеки (Fallback до сирого запиту).")
            return ValidationResult(
                approved=True,
                normalized_query=clean_query
            )