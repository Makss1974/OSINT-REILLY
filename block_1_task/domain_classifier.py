#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 1 — DOMAIN CLASSIFIER (Класифікатор онтологій)
Етап 1.2: Визначення цільових доменів знань та виокремлення ключових маркерів.
Path: /home/ubuntu/IT-PROJECTS/REILLY/block_1_task/domain_classifier.py
"""

import logging
import re
from typing import Dict, Any, List
from core_intelligence.router import ReillyLlmRouter

logger = logging.getLogger(__name__)

class DomainClassifier:
    """
    Компонент класифікації. Визначає тематичний домен OSINT-дослідження
    для активації відповідних низькорівневих аналітичних шарів.
    """
    def __init__(self, router: ReillyLlmRouter):
        self.router = router
        
        # Статичні сигнатурні маркери для евристичного резервного аналізу
        self.signatures = {
            "MILITARY_SECURITY": ["впк", "завод", "оборонн", "потужност", "ваканс", "маршрут", "армія", "зброя"],
            "ECONOMIC": ["тендер", "постачанн", "метал", "бюджет", "закупівл", "фінанс", "вартість"],
            "SOCIO_POLITICAL": ["протест", "вибори", "рейтинг", "мітинг", "соціолог", "настрій"]
        }

    def classify(self, normalized_query: str) -> Dict[str, Any]:
        """
        Головний метод класифікації запиту за онтологічними доменами.
        """
        logger.info("[Класифікатор] 🏷️ Визначення цільових доменів знань...")
        
        # Базова структура мета-даних домену
        domain_meta = {
            "domain": "GENERAL",
            "keywords": [],
            "target_urls": [],
            "confidence": 0.5
        }

        # 1. Автоматичний пошук URL-адрес у тексті запиту
        # Твій інфраструктурний колектор потребує прямих лінків, якщо користувач їх вказав
        urls = re.findall(r'https?://[^\s]+', normalized_query)
        if urls:
            domain_meta["target_urls"] = [url.strip(",.()\"'") for url in urls]
            logger.info("[Класифікатор] Знайдено прямі цільові URL: %s", domain_meta["target_urls"])

        # 2. Виклик ШІ-роутера для точного визначення контексту
        try:
            classifier_prompt = (
                f"Визнач домен знань для цього OSINT-запиту. Ожидані варіанти: "
                f"MILITARY_SECURITY, ECONOMIC, SOCIO_POLITICAL, SCIENTIFIC_TECH, PRIVATE.\n"
                f"Запит: {normalized_query}\n"
                f"Поверни відповідь у форматі одного слова-маркера домену."
            )
            
            ai_domain = self.router.execute_classification(classifier_prompt)
            
            if ai_domain and ai_domain.strip() in ["MILITARY_SECURITY", "ECONOMIC", "SOCIO_POLITICAL", "SCIENTIFIC_TECH", "PRIVATE"]:
                domain_meta["domain"] = ai_domain.strip()
                domain_meta["confidence"] = 0.9
                logger.info("[Класифікатор] ШІ визначив домен знань: %s", domain_meta["domain"])
            else:
                # Якщо ШІ повернув не валідний рядок, запускаємо локальну евристику
                logger.warning("[Класифікатор] Нестандартна відповідь ШІ. Вмикаємо локальні сигнатури.")
                domain_meta = self._run_heuristic_fallback(normalized_query, domain_meta)

        except Exception as e:
            logger.error("[Класифікатор] Помилка ШІ-аналізу контексту: %s.Fallback на евристику.", str(e))
            domain_meta = self._run_heuristic_fallback(normalized_query, domain_meta)

        # 3. Виділення базових пошукових тегів з тексту запиту (для Ешелону 1)
        words = normalized_query.lower().split()
        keywords = [w.strip(",.()\"'") for w in words if len(w) > 4 and w not in ["проаналізуй", "стан", "році", "динаміку"]]
        domain_meta["keywords"] = list(set(keywords))[:5]

        return domain_meta

    def _run_heuristic_fallback(self, text: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Локальний евристичний аналізатор тексту за збігом ключових основ слів."""
        lower_text = text.lower()
        max_matches = 0
        detected_domain = "GENERAL"

        for domain_name, markers in self.signatures.items():
            matches = sum(1 for marker in markers if marker in lower_text)
            if matches > max_matches:
                max_matches = matches
                detected_domain = domain_name

        meta["domain"] = detected_domain
        meta["confidence"] = 0.7
        logger.info("[Класифікатор Евристика] Визначено резервний домен: %s (збігів: %d)", detected_domain, max_matches)
        return meta