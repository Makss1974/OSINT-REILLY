#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 2 — Infrastructure HTML Collector with Maxwell's Demon
Path: block_2_inform/data_collection/infra_collector.py
Line Length Limit: 100 characters

Fetches raw HTML pages using Bright Data and Filters out anti-bot/empty trash sheets.
"""

import logging
import re
from typing import Any, Dict, Optional
from block_2_inform.data_collection.brightdata_client import BrightDataClient

logger = logging.getLogger(__name__)


class MaxwellDemonFilter:
    """Низькорівневий фільтр Максвелла для відсікання цифрового сміття та капч."""

    # Маркери систем захисту та блокувань (Cloudflare, PerimeterX, DDOS-Guard)
    ANTI_BOT_MARKERS = [
        r"captcha", r"cloudflare", r"ray id", r"checking your browser",
        r"ddos-guard", r"access denied", r"sucuri", r"robot check"
    ]

    # Маркери порожніх сторінок або помилок хостингу
    TRASH_MARKERS = [
        r"403 forbidden", r"404 not found", r"502 bad gateway",
        r"500 internal server error", r"site under construction",
        r"suspicious activity", r"ip has been blocked"
    ]

    @classmethod
    def is_valid_payload(cls, html_content: str) -> bool:
        """
        Аналізує сирий HTML. Повертає True, якщо сторінка жива і корисна.
        Повертає False, якщо виявлено капчу або сміття (Демон Максвелла).
        """
        if not html_content or len(html_content.strip()) < 200:
            logger.warning("Maxwell's Demon: Blocked empty or micro-sized HTML response.")
            return False

        content_lower = html_content.lower()

        # 1. Перевірка на антифрод-системи
        for marker in cls.ANTI_BOT_MARKERS:
            if re.search(marker, content_lower):
                logger.warning(f"Maxwell's Demon: Blocked anti-bot wall page! Marker: [{marker}]")
                return False

        # 2. Перевірка на стандартні серверні заглушки та помилки
        for marker in cls.TRASH_MARKERS:
            if re.search(marker, content_lower):
                logger.warning(f"Maxwell's Demon: Blocked error/trash page! Marker: [{marker}]")
                return False

        return True


class InfraCollector:
    """Інфраструктурний колектор сирого HTML контенту з інтегрованим фільтром."""

    def __init__(self, bd_client: Optional[BrightDataClient] = None):
        # Якщо клієнт Bright Data не переданий, створюємо дефолтний
        self.client = bd_client or BrightDataClient()

    def collect_target_html(self, url: str) -> Dict[str, Any]:
        """
        Скачує цільову веб-сторінку через Bright Data та пропускає через Демона.
        """
        logger.info(f"Initiating infrastructure HTML collection for: {url}")
        
        # Виклик твого бойового клієнта Bright Data
        raw_html = self.client.fetch_page(url)

        if not raw_html:
            return {"status": "FAILED_NETWORK_ERROR", "html": ""}

        # Запускаємо Демона Максвелла для оцінки якості зрізу
        if not MaxwellDemonFilter.is_valid_payload(raw_html):
            return {"status": "FAILED_BLOCKED_OR_TRASH", "html": ""}

        logger.info(f"Infrastructure page passed Maxwell filter successfully: {url}")
        return {
            "status": "SUCCESS",
            "html": raw_html
        }


# --- Швидкий локальний тест-драйв модуля ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = InfraCollector()
    
    # 1. Тест Демона на Cloudflare заглушку
    fake_cloudflare_page = "<html><head><title>Just a moment...</title></head><body>cloudflare ray id</body></html>"
    is_ok = MaxwellDemonFilter.is_valid_payload(fake_cloudflare_page)
    print(f"Тест 1 (Cloudflare заглушка) — Пройшов фільтр? -> {is_ok} (Очікується: False)")

    # 2. Тест Демона на корисну сторінку
    fake_good_page = "<html><body><h1>Номенклатура продукції заводу</h1><p>Цех №1...</p></body></html>"
    is_ok_2 = MaxwellDemonFilter.is_valid_payload(fake_good_page)
    print(f"Тест 2 (Корисна сторінка) — Пройшов фільтр? -> {is_ok_2} (Очікується: True)")