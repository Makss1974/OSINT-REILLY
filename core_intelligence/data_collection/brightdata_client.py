#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 2 — BrightData Gateway (Data Collection Entry Point)
Path: core_intelligence/data_collection/brightdata_client.py
Line Length Limit: 100 characters

Integration contract:
  INPUT  ← ActionProgram.search_tasks[].initial_queries + bright_data_tool (Block 1)
  OUTPUT → Raw JSON results / HTML strings → /state/cache/ (Block 3/4 consumers)
"""

import os
import time
import random
import logging
from typing import Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Bright Data SERP API endpoint (POST, returns structured JSON)
SERP_API_ENDPOINT = "https://api.brightdata.com/serp"

# Bright Data proxy gateway host (используется как HTTP/HTTPS proxy tunnel)
BRIGHTDATA_PROXY_HOST = "brd.superproxy.io"
BRIGHTDATA_PROXY_PORT = 22225

# HTTP request timeouts (seconds)
SERP_TIMEOUT_SEC    = 30
PROXY_TIMEOUT_SEC   = 45

# Retry policy
MAX_RETRIES     = 3
RETRY_BASE_WAIT = 2.0   # seconds (exponential backoff base)

# Human-like pause range between sequential SERP calls (seconds)
HUMAN_PAUSE_MIN = 1.5
HUMAN_PAUSE_MAX = 4.5

# Fingerprint pool — rotated per request to mimic real browser diversity
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]


# ─────────────────────────────────────────────────────────────────────────────
# BrightDataClient
# ─────────────────────────────────────────────────────────────────────────────

class BrightDataClient:
    """
    Єдиний гейтвей Блоку 2 для всіх мережевих операцій через інфраструктуру Bright Data.

    Забезпечує два бойових канали:
      A) fetch_serp()            — SEMANTIC пошук через SERP API (Google Dorks, новини)
      B) fetch_html_via_proxy()  — QUANTITATIVE / SPATIAL_INFRA скачування через
                                   резидентський / мобільний проксі-тунель

    Автоматично реалізує:
      - Каскадний retry з exponential backoff
      - Fingerprint morphing (ротація User-Agent на кожен запит)
      - Human-like паузи між послідовними SERP-запитами
      - Структурований лог усіх операцій для аудиту
    """

    def __init__(self):
        load_dotenv()

        self.api_key  = os.getenv("BRIGHTDATA_API_KEY")
        self.zone_res = os.getenv("BRIGHTDATA_ZONE_RESIDENTIAL", "residential")

        # ── Hard security gate: без ключа система не стартує ──────────────────
        if not self.api_key:
            logger.critical(
                "BRIGHTDATA_API_KEY is missing. "
                "Set it in .env or as an environment variable before launching Block 2."
            )
            raise EnvironmentError(
                "Critical: BRIGHTDATA_API_KEY missing in environment. "
                "Block 2 cannot operate without authenticated access."
            )

        logger.info(
            "[BrightDataClient] Initialized | zone=%s | key=***%s",
            self.zone_res,
            self.api_key[-4:],   # Логуємо лише хвіст ключа — не повний токен
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Public Method A: SERP API — Semantic / Discursive search
    # ─────────────────────────────────────────────────────────────────────────

    def fetch_serp(
        self,
        queries: list[str],
        country: str = "us",
        language: str = "en",
        results_per_query: int = 10,
    ) -> list[dict]:
        """
        Збір структурованої пошукової видачі Google через Bright Data SERP API.

        Призначення: SearchType.SEMANTIC
          — новини, аналітика think-tanks, прес-релізи, Google Dorks.

        Args:
            queries:           Список сформованих пошукових запитів / dorks з Block 1.
            country:           ISO-код країни для геолокованої видачі (напр. "ru", "us").
            language:          Мова результатів (напр. "uk", "ru", "en").
            results_per_query: Кількість результатів на один запит (максимум 100).

        Returns:
            Масив словників — кожен елемент = повна SERP-відповідь для одного запиту.
            Структура кожного елементу:
            {
                "query":   "<вхідний рядок запиту>",
                "status":  "ok" | "error",
                "results": [ { "title": ..., "url": ..., "snippet": ... }, ... ],
                "raw":     <повний сирий JSON від API>     # для глибокого аудиту
            }
        """
        if not queries:
            logger.warning("[SERP] Empty query list received. Returning empty results.")
            return []

        all_results: list[dict] = []

        logger.info("[SERP] Starting batch | %d queries | country=%s", len(queries), country)

        for idx, query in enumerate(queries, 1):
            logger.info("[SERP] Query %d/%d: %.80s", idx, len(queries), query)

            result = self._fetch_serp_single(
                query=query,
                country=country,
                language=language,
                num=results_per_query,
            )
            all_results.append(result)

            # Human-like пауза між запитами — запобігає блокуванню за патерном
            if idx < len(queries):
                pause = random.uniform(HUMAN_PAUSE_MIN, HUMAN_PAUSE_MAX)
                logger.debug("[SERP] Human-pause: %.1fs before next query.", pause)
                time.sleep(pause)

        ok_count  = sum(1 for r in all_results if r["status"] == "ok")
        err_count = len(all_results) - ok_count
        logger.info("[SERP] Batch complete | ok=%d | errors=%d", ok_count, err_count)

        return all_results

    # ─────────────────────────────────────────────────────────────────────────
    # Public Method B: Proxy tunnel — Quantitative / Spatial-Infra scraping
    # ─────────────────────────────────────────────────────────────────────────

    def fetch_html_via_proxy(
        self,
        url: str,
        zone: Optional[str] = None,
        country_iso: Optional[str] = None,
    ) -> str:
        """
        Пряме скачування HTML-сторінки через проксі-тунель Bright Data.

        Призначення: SearchType.QUANTITATIVE та SearchType.SPATIAL_INFRA
          — держпортали тендерів, реєстри вакансій ВПК, митні бази, фінзвітність.

        Cascade зон (відповідно до ТЗ Блоку 3):
          zone="residential"  → ISP Residential proxies (домашній інтернет)
          zone="mobile"       → Mobile 3G/4G/5G (найвища довіра, важко забанити)
          zone="datacenter"   → Datacenter proxies (швидкі, для відкритих даних)

        Args:
            url:         Цільова URL-адреса для скачування.
            zone:        Bright Data зона (overrides .env default).
            country_iso: ISO-код країни вихідного IP (напр. "RU", "DE").
                         None = автоматичний вибір Bright Data.

        Returns:
            Сирий HTML-код сторінки (str). При невдачі після всіх retry — порожній рядок.
        """
        active_zone = zone or self.zone_res
        logger.info("[PROXY] Fetching URL via zone=%s | %s", active_zone, url)

        proxy_url = self._build_proxy_url(active_zone, country_iso)
        proxies   = {"http": proxy_url, "https": proxy_url}
        headers   = self._build_headers()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(
                    url,
                    proxies=proxies,
                    headers=headers,
                    timeout=PROXY_TIMEOUT_SEC,
                    verify=True,  # SSL verification залишається активним
                )

                if response.status_code == 200:
                    size_kb = len(response.content) / 1024
                    logger.info(
                        "[PROXY] ✅ Success | status=200 | size=%.1fKB | attempt=%d",
                        size_kb, attempt,
                    )
                    return response.text

                # Cascade: 403/429 = блокування → логуємо та пробуємо знову
                logger.warning(
                    "[PROXY] HTTP %d on attempt %d/%d | url=%s",
                    response.status_code, attempt, MAX_RETRIES, url,
                )

            except requests.exceptions.ProxyError as exc:
                logger.warning("[PROXY] ProxyError attempt %d/%d: %s", attempt, MAX_RETRIES, exc)

            except requests.exceptions.ConnectionError as exc:
                logger.warning(
                    "[PROXY] ConnectionError attempt %d/%d: %s", attempt, MAX_RETRIES, exc
                )

            except requests.exceptions.Timeout:
                logger.warning(
                    "[PROXY] Timeout (%ds) on attempt %d/%d",
                    PROXY_TIMEOUT_SEC, attempt, MAX_RETRIES
                )

            # Exponential backoff перед наступною спробою
            if attempt < MAX_RETRIES:
                wait = RETRY_BASE_WAIT * (2 ** (attempt - 1))
                logger.info("[PROXY] Retry in %.1fs...", wait)
                time.sleep(wait)

        logger.error("[PROXY] ❌ All %d attempts failed for URL: %s", MAX_RETRIES, url)
        return ""

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _fetch_serp_single(
        self,
        query: str,
        country: str,
        language: str,
        num: int,
    ) -> dict:
        """
        Виконує один SERP-запит з retry-логікою.
        Повертає нормалізований словник результату незалежно від успіху / збою.
        """
        payload = {
            "query":    query,
            "country":  country,
            "language": language,
            "num":      num,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
            **self._build_headers(),
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.post(
                    SERP_API_ENDPOINT,
                    json=payload,
                    headers=headers,
                    timeout=SERP_TIMEOUT_SEC,
                )

                if response.status_code == 200:
                    raw_data = response.json()
                    organic  = raw_data.get("organic", [])
                    logger.debug(
                        "[SERP] ✅ Query returned %d organic results.", len(organic)
                    )
                    return {
                        "query":   query,
                        "status":  "ok",
                        "results": self._normalize_serp_results(organic),
                        "raw":     raw_data,
                    }

                logger.warning(
                    "[SERP] HTTP %d on attempt %d/%d",
                    response.status_code, attempt, MAX_RETRIES,
                )

            except requests.exceptions.Timeout:
                logger.warning("[SERP] Timeout attempt %d/%d", attempt, MAX_RETRIES)

            except requests.exceptions.RequestException as exc:
                logger.warning(
                    "[SERP] RequestException attempt %d/%d: %s",
                    attempt, MAX_RETRIES, exc,
                )

            if attempt < MAX_RETRIES:
                wait = RETRY_BASE_WAIT * (2 ** (attempt - 1))
                time.sleep(wait)

        # Повертаємо структурований збій, а не виняток — pipeline не обривається
        return {"query": query, "status": "error", "results": [], "raw": {}}

    def _build_proxy_url(self, zone: str, country_iso: Optional[str]) -> str:
        """
        Формує рядок підключення до Bright Data proxy-тунелю.
        Формат: http://brd-customer-<key>-zone-<zone>[-country-<iso>]:<port>@host:port
        """
        username = f"brd-customer-{self.api_key}-zone-{zone}"
        if country_iso:
            username += f"-country-{country_iso.lower()}"
        host = BRIGHTDATA_PROXY_HOST
        port = BRIGHTDATA_PROXY_PORT
        return f"http://{username}:{port}@{host}:{port}"

    @staticmethod
    def _build_headers() -> dict:
        """Повертає заголовки з випадковим User-Agent для Fingerprint Morphing."""
        return {
            "User-Agent":      random.choice(_USER_AGENTS),
            "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.7,en-US;q=0.5,en;q=0.3",
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection":      "keep-alive",
            "DNT":             "1",
        }

    @staticmethod
    def _normalize_serp_results(organic: list) -> list[dict]:
        """
        Нормалізує сирі результати SERP до єдиного формату.
        Захищає від відсутніх полів у відповіді API.
        """
        normalized = []
        for item in organic:
            normalized.append({
                "title":   item.get("title", ""),
                "url":     item.get("link", item.get("url", "")),
                "snippet": item.get("snippet", item.get("description", "")),
                "source":  item.get("source", ""),
                "rank":    item.get("position", item.get("rank", 0)),
            })
        return normalized


# ─────────────────────────────────────────────────────────────────────────────
# Smoke-test (для ручного запуску: python brightdata_client.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        client = BrightDataClient()

        # Тест A: SERP — один запит з реального пайплайну Block 1
        serp_results = client.fetch_serp(
            queries=['site:gov.ru "тендер" "Уралвагонзавод" 2024'],
            country="ru",
            language="ru",
        )
        print(f"\n[SERP TEST] Returned {len(serp_results)} result blocks.")
        if serp_results:
            first = serp_results[0]
            print(f"  Status: {first['status']} | Results count: {len(first['results'])}")

        # Тест B: Proxy — скачування відкритої сторінки через резидентський тунель
        html = client.fetch_html_via_proxy(
            url="https://httpbin.org/ip",  # Відповідає реальним IP вихідного вузла
            zone="residential",
        )
        print(f"\n[PROXY TEST] HTML length: {len(html)} chars")
        print(f"  First 200 chars: {html[:200]}")

    except EnvironmentError as e:
        print(f"\n[SMOKE TEST ABORTED] {e}")
        print("  → Create a .env file with BRIGHTDATA_API_KEY and BRIGHTDATA_ZONE_RESIDENTIAL.")
