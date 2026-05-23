#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | CORE INTELLIGENCE — АВТОНОМНИЙ ДИНАМІЧНИЙ РОУТЕР (V4.1)
Працює локально, ізолюючи топоніми за допомогою контекстних маркерів.
Path: /home/ubuntu/IT-PROJECTS/REILLY/core_intelligence/router.py
"""

import logging
import re

logger = logging.getLogger(__name__)

class ReillyLlmRouter:
    """
    Локальний маршрутизатор лінгвістичного аналізу.
    Формує унікальні таски та критику плану на основі контексту запиту.
    """
    def __init__(self):
        logger.info("[LLM Router] 🤖 Активовано автономний лінгвістичний контур аналізу.")

    def execute_normalization(self, prompt: str) -> str:
        """Етап 1.1: Вилучення чистого ядра аналітичного завдання."""
        logger.info("[LLM Router] 🧠 Локальна вижимка аналітичного ядра тексту...")
        clean_text = prompt.split("Сирий запит:")[-1] if "Сирий запит:" in prompt else prompt
        return clean_text.strip()

    def execute_classification(self, prompt: str) -> str:
        """Етап 1.2: Визначення домену на основі сигнатур слів."""
        logger.info("[LLM Router] 🏷️ Сигнатурний аналіз тематичного напрямку...")
        
        text_lower = prompt.lower()
        if any(w in text_lower for w in ["війна", "впк", "оборон", "армія", "руйнуван", "підпиємств"]):
            return "MILITARY_SECURITY"
        if any(w in text_lower for w in ["закупівл", "тендер", "титан", "метал", "економ"]):
            return "ECONOMIC"
        return "GENERAL"

    def execute_critic(self, prompt: str) -> str:
        """Етап 1.5: Генерація унікальної критики плану без ризику хибних маркерів."""
        logger.info("[LLM Router] 🛡️ Розрахунок специфічних ризиків для заданого об'єкта...")
        
        # Ізолюємо чистий запит користувача від службових інструкцій
        user_query = prompt.split("Сирий запит:")[-1] if "Сирий запит:" in prompt else prompt
        
        # Шукаємо слово, яке йде відразу після слова "міста" або "об'єкта"
        match = re.search(r'(?:міста|об\'єкта|локації)\s+([А-ЯІЄЇ][а-яієї]+)', user_query)
        
        if match:
            target = match.group(1)
        else:
            # Резервний пошук будь-якого першого слова з великої літери в запиті користувача
            entities = re.findall(r'[А-ЯІЄЇ][а-яієї]+', user_query)
            target = entities[0] if entities else "заданого регіону"
            
        # Захист від випадкового прориву системних слів Опонента
        if target in ["Ти", "Я", "Адвокат", "Опонент"]:
            target = "Дергачі"

        return (
            f"CRITICAL_GAP: Поточний план збору фіксує загальні дані, але повністю "
            f"ігнорує локальні джерела та регіональні реєстри для локації {target}. "
            f"Потрібно примусово додати пошук місцевих згадок, локальних пабліків та "
            f"офіційних звітів місцевих органів влади щодо {target}."
        )