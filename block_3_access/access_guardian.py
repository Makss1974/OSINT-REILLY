#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 3 — ACCESS GUARDIAN (Интелектуальний проксі-камуфляж)
Реалізує трирівневий каскад пулів Bright Data: Резидентські ISP → Мобільні 4G → Web Unlocker.
Path: /home/ubuntu/IT-PROJECTS/REILLY/block_3_access/access_guardian.py
"""

import logging
import random
import time
from enum import Enum
from typing import Dict, Any, Optional
from block_2_inform.data_collection.brightdata_client import BrightDataClient

logger = logging.getLogger(__name__)

class ProxyPool(str, Enum):
    """Трирівневий каскад пулів Bright Data відповідно до ТЗ."""
    RESIDENTIAL_ISP = "POOL_1_RESIDENTIAL_ISP"   # Домашній інтернет цільової країни
    MOBILE_4G       = "POOL_2_MOBILE_4G"          # Мобільні IP (найвища довіра вузлів)
    WEB_UNLOCKER    = "POOL_3_WEB_UNLOCKER"       # Екстрений ешелон (емуляція браузера, обхід капчі)

class AccessGuardian:
    """
    Охоронець доступу. Забезпечує інтелектуальну конвеєрну обробку HTTP-запитів.
    Захищає Демона Максвелла від блокувань за допомогою автоматичної ротації зон.
    """
    def __init__(self, bd_client: Optional[BrightDataClient] = None, country_iso: str = "RU"):
        self.bd_client = bd_client or BrightDataClient()
        self.country_iso = country_iso
        self._request_count = 0
        self._blocked_count = 0

        # Списки юзер-агентів для камуфлювання під реальних аналітиків
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/123.0"
        ]

    def execute_request_with_cascade(self, url: str, search_type: str = "SPATIAL_INFRA") -> str:
        """
        Головний бойовий метод каскадного збору.
        Якщо пул нижнього рівня падає або фіксує бан, автоматично піднімає наступний пул.
        """
        self._request_count += 1
        logger.info("[Guardian] 🛡️ Запуск каскадного запиту для цілі: %s", url)

        # Визначаємо черговість пулів залежно від типу таски
        # Якщо таска вже маркована як високого ризику, відразу стартуємо з Мобільних IP
        if search_type in ["TEMPORAL_ANOMALY", "CORRELATION_CROSS"]:
            cascade = [ProxyPool.MOBILE_4G, ProxyPool.WEB_UNLOCKER]
        else:
            cascade = [ProxyPool.RESIDENTIAL_ISP, ProxyPool.MOBILE_4G, ProxyPool.WEB_UNLOCKER]

        html_content = ""
        for attempt, pool in enumerate(cascade, 1):
            try:
                logger.info("[Guardian] Спроба %d: Використовуємо %s", attempt, pool.value)
                
                # Мапуємо наш Enum на реальні зони Bright Data
                zone_map = {
                    ProxyPool.RESIDENTIAL_ISP: "residential",
                    ProxyPool.MOBILE_4G: "mobile",
                    ProxyPool.WEB_UNLOCKER: "bd_unlocker"
                }
                zone = zone_map[pool]

                # Фізичний запит через твій бойовий клієнт
                html_content = self.bd_client.fetch_html_via_proxy(
                    url=url, 
                    zone=zone, 
                    country_iso=self.country_iso
                )

                # Перевірка на маркери блокування (Капча, Cloudflare, 403 Forbidden)
                if self._is_blocked(html_content):
                    logger.warning("[Guardian] ⚠️ Фіксуємо маркер блокування або капчу на пулі %s!", pool.value)
                    self._blocked_count += 1
                    # Експоненційна затримка перед наступним ешелоном каскаду
                    time.sleep(2.0 ** attempt)
                    continue  # Переходимо до наступного пулу каскаду

                logger.info("[Guardian] ✅ Запит успішно виконано за допомогою пулу %s", pool.value)
                return html_content

            except Exception as e:
                logger.error("[Guardian] 💥 Збій тунелю на пулі %s: %s", pool.value, str(e))
                time.sleep(1.5 * attempt)
                continue

        # Якщо весь каскад пробитий, повертаємо захищений аварійний бейзлайн
        logger.error("[Guardian] 🚨 КРИТИЧНИЙ ЗБІЙ: Весь проксі-каскад Bright Data заблоковано!")
        return "<html><body>[ERROR_BLOCKED] Контур захисту цілі виявився сильнішим за проксі-каскад.</body></html>"

    def _is_blocked(self, html: str) -> bool:
        """Перевірка сирого тексту сторінки на наявність систем протидії парсингу."""
        if not html or len(html) < 400:
            return True
            
        lower_html = html.lower()
        block_markers = [
            "captcha", "cloudflare", "sucuri", "ddos protection", 
            "access denied", "403 forbidden", "робот", "заблокирован"
        ]
        return any(marker in lower_html for marker in block_markers)

    def get_guardian_status(self) -> Dict[str, Any]:
        """Повертає статистику пробиття та банів для Блоку 5."""
        block_rate = self._blocked_count / max(self._request_count, 1)
        return {
            "total_monitored_requests": self._request_count,
            "blocked_events": self._blocked_count,
            "integrity_index_pct": round((1.0 - block_rate) * 100, 1)
        }