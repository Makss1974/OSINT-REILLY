#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 2 — Infrastructure HTML Collector (Maxwell Daemon Contour)
Path: core_intelligence/data_collection/infra_collector.py
Line Length Limit: 100 characters

Cognitive architecture:
  «Heavy assault unit» — bypasses directly to target web resources
  (state tender portals, closed logistics nodes, defense-factory job boards)
  and retrieves raw HTML for deep audit.

  Maxwell Daemon sorts every page into one of two baskets:
    HOT_SIGNAL     → new tenders, vacancy deltas, critical content change → Block 4 queue
    STALE_BASELINE → empty page, CAPTCHA, or byte-identical to previous sweep → archive

Integration contract:
  INPUT  ← ActionProgram dict (Block 1), target URLs inside search_tasks[].initial_queries
  OUTPUT → Manifest JSON + cached HTML files under ./state/infra_cache/
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

from .brightdata_client import BrightDataClient

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# SearchType markers this collector handles
INFRA_SEARCH_TYPES = {"SPATIAL_INFRA", "QUANTITATIVE"}

# Maxwell Daemon thresholds
MIN_CONTENT_CHARS   = 500    # Below this — page is considered empty / blocked
CAPTCHA_MARKERS     = [      # Strings that betray a CAPTCHA / block wall
    "captcha", "cloudflare", "access denied", "robot", "403 forbidden",
    "enable javascript", "checking your browser", "ddos-guard",
]
HOT_DELTA_THRESHOLD = 0.03   # 3 % change in content hash → HOT_SIGNAL

# Proxy zone cascade (concept from Block 3 spec)
ZONE_CASCADE = ["residential", "mobile", "datacenter"]

# Default cache subdirectory
DEFAULT_CACHE_DIR = "./state/infra_cache"

# Manifest filename
MANIFEST_FILENAME = "infra_manifest.json"


# ─────────────────────────────────────────────────────────────────────────────
# InfraCollector
# ─────────────────────────────────────────────────────────────────────────────

class InfraCollector:
    """
    Інфраструктурний HTML-колектор Блоку 2.

    Виконує прямий прорив на цільові ресурси через резидентський проксі-тунель
    і пропускає кожну завантажену сторінку крізь Демона Максвелла —
    фоновий ентропійний фільтр, що відокремлює живі сигнали від фонового шуму.

    Збирає таски типу SPATIAL_INFRA та QUANTITATIVE з ActionProgram.
    """

    def __init__(
        self,
        bd_client: BrightDataClient,
        cache_dir: str = DEFAULT_CACHE_DIR,
    ):
        """
        Args:
            bd_client:  Ініціалізований BrightDataClient («руки» Блоку 2).
            cache_dir:  Шлях до папки для сирого HTML-кешу та маніфестів.
        """
        self.bd_client = bd_client
        self.cache_dir = cache_dir

        # Папки для двох кошиків Демона
        self.hot_dir  = os.path.join(cache_dir, "hot")
        self.cold_dir = os.path.join(cache_dir, "cold")
        self.meta_dir = os.path.join(cache_dir, "baseline_meta")

        for directory in (self.hot_dir, self.cold_dir, self.meta_dir):
            os.makedirs(directory, exist_ok=True)

        logger.info(
            "[InfraCollector] Ready | cache=%s | hot=%s | cold=%s",
            cache_dir, self.hot_dir, self.cold_dir,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def collect_infra_pipeline(
        self,
        action_program: dict,
        zone: str = "residential",
        country_iso: Optional[str] = None,
        save_manifest: bool = True,
    ) -> dict:
        """
        Повний цикл інфраструктурного збору прямим проривом через проксі.

        Args:
            action_program: Словник ActionProgram.to_dict() з виходу Блоку 1.
            zone:           Стартова зона Bright Data (каскад: residential→mobile).
            country_iso:    ISO-код країни вихідного IP (напр. "RU").
            save_manifest:  Якщо True — записує manifest JSON до cache_dir.

        Returns:
            Маніфест збору з artifacts[] для передачі до Block 4.
        """
        raw_query    = action_program.get("raw_query", "")
        search_tasks = action_program.get("search_tasks", [])

        logger.info(
            "[InfraCollector] Pipeline START | query=%.70s | tasks=%d",
            raw_query, len(search_tasks),
        )

        # ── Крок 1: Фільтруємо відповідні таски ──────────────────────────────
        infra_tasks = [
            t for t in search_tasks
            if t.get("search_type") in INFRA_SEARCH_TYPES
        ]

        if not infra_tasks:
            logger.warning(
                "[InfraCollector] No SPATIAL_INFRA / QUANTITATIVE tasks found."
            )
            return self._build_manifest(raw_query, [])

        # ── Крок 2: Збираємо всі URL-цілі ────────────────────────────────────
        targets = self._extract_targets(infra_tasks)
        logger.info(
            "[InfraCollector] Targets extracted: %d URL(s) across %d task(s).",
            len(targets), len(infra_tasks),
        )

        if not targets:
            logger.warning("[InfraCollector] No valid URLs found in initial_queries.")
            return self._build_manifest(raw_query, [])

        # ── Крок 3: Обхід цілей, Демон Максвелла, збереження ─────────────────
        artifacts = []
        for idx, (url, search_type) in enumerate(targets, 1):
            logger.info(
                "[InfraCollector] Target %d/%d [%s]: %s",
                idx, len(targets), search_type, url,
            )
            artifact = self._process_target(url, search_type, zone, country_iso)
            artifacts.append(artifact)

        # ── Крок 4: Маніфест ──────────────────────────────────────────────────
        manifest = self._build_manifest(raw_query, artifacts)

        if save_manifest:
            manifest_path = self._save_manifest(manifest)
            manifest["manifest_file"] = manifest_path

        hot  = manifest["statistics"]["hot_signals"]
        cold = manifest["statistics"]["cold_baseline"]
        logger.info(
            "[InfraCollector] Pipeline COMPLETE ✅ | "
            "total=%d | HOT=%d | COLD=%d",
            len(artifacts), hot, cold,
        )
        return manifest

    # ─────────────────────────────────────────────────────────────────────────
    # Maxwell Daemon
    # ─────────────────────────────────────────────────────────────────────────

    def _maxwell_daemon_filter(self, url: str, current_html: str) -> dict:
        """
        Фоновий Демон Максвелла — ентропійний сортувальник.

        Оцінює HTML-сторінку за трьома критеріями:
          1. Вага контенту  — «порожня» сторінка чи є реальний текст?
          2. Маркери блоку  — капча, CloudFlare, Access Denied?
          3. Дельта змін    — чи відрізняється від попереднього сканування?

        Returns:
            {
              "status":        "HOT" | "COLD",
              "reason":        str,           # Причина рішення для аудиту
              "content_delta": bool,          # True якщо зміни виявлено
              "content_hash":  str,           # SHA-256 чистого тексту
              "clean_length":  int,           # Кількість корисних символів
            }
        """
        # ── Фаза 1: Видалення HTML-тегів, підрахунок корисного тексту ─────────
        clean_text   = self._strip_html(current_html)
        clean_length = len(clean_text.strip())

        # ── Фаза 2: Перевірка мінімального порогу контенту ────────────────────
        if clean_length < MIN_CONTENT_CHARS:
            return {
                "status":        "COLD",
                "reason":        (
                    f"STALE_BASELINE: content too short "
                    f"({clean_length} < {MIN_CONTENT_CHARS} chars). "
                    "Page likely empty or blocked."
                ),
                "content_delta": False,
                "content_hash":  "",
                "clean_length":  clean_length,
            }

        # ── Фаза 3: Перевірка маркерів капчі / блокування ─────────────────────
        lower_html = current_html.lower()
        for marker in CAPTCHA_MARKERS:
            if marker in lower_html:
                return {
                    "status":        "COLD",
                    "reason":        (
                        f"STALE_BASELINE: CAPTCHA/block wall detected "
                        f"(marker: '{marker}')."
                    ),
                    "content_delta": False,
                    "content_hash":  "",
                    "clean_length":  clean_length,
                }

        # ── Фаза 4: SHA-256 хеш чистого тексту для порівняння з baseline ──────
        current_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
        previous_hash, has_baseline = self._load_baseline_hash(url)

        content_delta = False
        if has_baseline:
            content_delta = (current_hash != previous_hash)
            if not content_delta:
                return {
                    "status":        "COLD",
                    "reason":        (
                        "STALE_BASELINE: content hash identical to previous sweep. "
                        "No structural changes detected."
                    ),
                    "content_delta": False,
                    "content_hash":  current_hash,
                    "clean_length":  clean_length,
                }

        # ── Фаза 5: Зберігаємо новий baseline та повертаємо HOT ───────────────
        self._save_baseline_hash(url, current_hash)
        reason = (
            "HOT_SIGNAL: content changed since last sweep."
            if has_baseline
            else "HOT_SIGNAL: first-time capture — baseline established."
        )

        return {
            "status":        "HOT",
            "reason":        reason,
            "content_delta": content_delta,
            "content_hash":  current_hash,
            "clean_length":  clean_length,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Internal pipeline helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _process_target(
        self,
        url: str,
        search_type: str,
        zone: str,
        country_iso: Optional[str],
    ) -> dict:
        """
        Обробляє одну URL-ціль: завантаження → Демон → збереження.
        При помилці або порожній відповіді повертає COLD-артефакт.
        """
        # Завантаження через проксі-тунель
        html = self.bd_client.fetch_html_via_proxy(
            url=url,
            zone=zone,
            country_iso=country_iso,
        )

        # Захист: fetch_html_via_proxy повертає "" при повній відмові
        if not html:
            logger.warning("[Maxwell] Empty response for URL: %s", url)
            return {
                "url":        url,
                "search_type": search_type,
                "status":     "COLD",
                "cache_file": "",
                "notes":      "FETCH_FAILED: proxy returned empty response after all retries.",
            }

        # Пропускаємо крізь Демона Максвелла
        daemon_result = self._maxwell_daemon_filter(url, html)
        status        = daemon_result["status"]   # "HOT" or "COLD"

        logger.info(
            "[Maxwell] %s | %s | delta=%s | chars=%d | %s",
            status, url[:60],
            daemon_result["content_delta"],
            daemon_result["clean_length"],
            daemon_result["reason"][:70],
        )

        # Зберігаємо HTML у відповідний кошик
        cache_file = self._save_html(url, html, status)

        return {
            "url":          url,
            "search_type":  search_type,
            "status":       status,
            "cache_file":   cache_file,
            "content_hash": daemon_result.get("content_hash", ""),
            "clean_length": daemon_result.get("clean_length", 0),
            "content_delta": daemon_result.get("content_delta", False),
            "notes":        daemon_result["reason"],
        }

    @staticmethod
    def _extract_targets(tasks: list[dict]) -> list[tuple[str, str]]:
        """
        Витягує URL-цілі з initial_queries.
        Повертає список кортежів (url, search_type).
        Рядки, що не починаються з http, пропускаються (це dork'и, не URL-и).
        """
        targets = []
        for task in tasks:
            search_type = task.get("search_type", "SPATIAL_INFRA")
            for query in task.get("initial_queries", []):
                if query.strip().startswith("http"):
                    targets.append((query.strip(), search_type))
                else:
                    logger.debug(
                        "[InfraCollector] Skipping non-URL query: %.60s", query
                    )
        return targets

    # ─────────────────────────────────────────────────────────────────────────
    # Baseline hash persistence (Maxwell Daemon memory)
    # ─────────────────────────────────────────────────────────────────────────

    def _url_slug(self, url: str) -> str:
        """Перетворює URL у безпечний ідентифікатор файлу (SHA-1 від URL)."""
        return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]

    def _baseline_path(self, url: str) -> str:
        return os.path.join(self.meta_dir, f"{self._url_slug(url)}.hash")

    def _load_baseline_hash(self, url: str) -> tuple[str, bool]:
        """
        Завантажує збережений хеш попереднього сканування.
        Повертає (hash_string, exists).
        """
        path = self._baseline_path(url)
        if not os.path.exists(path):
            return "", False
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip(), True
        except OSError:
            return "", False

    def _save_baseline_hash(self, url: str, content_hash: str) -> None:
        """Зберігає SHA-256 хеш поточного скану як новий baseline."""
        path = self._baseline_path(url)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content_hash)
        except OSError as exc:
            logger.warning("[Maxwell] Cannot save baseline hash for %s: %s", url, exc)

    # ─────────────────────────────────────────────────────────────────────────
    # Cache I/O
    # ─────────────────────────────────────────────────────────────────────────

    def _save_html(self, url: str, html: str, status: str) -> str:
        """
        Зберігає HTML у «гарячий» або «холодний» кошик.
        Ім'я файлу: <url_slug>_<timestamp>_<status>.html
        """
        timestamp   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        url_slug    = self._url_slug(url)
        filename    = f"{url_slug}_{timestamp}_{status.lower()}.html"
        target_dir  = self.hot_dir if status == "HOT" else self.cold_dir
        filepath    = os.path.join(target_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8", errors="replace") as f:
                # Зберігаємо оригінальний URL у HTML-коментарі для трасування
                f.write(f"<!-- SOURCE_URL: {url} -->\n")
                f.write(html)
            logger.debug("[InfraCollector] HTML saved → %s", filepath)
        except OSError as exc:
            logger.error("[InfraCollector] Cannot save HTML for %s: %s", url, exc)
            return ""

        return filepath

    def _save_manifest(self, manifest: dict) -> str:
        """Записує фінальний JSON-маніфест у корінь cache_dir."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename  = f"infra_manifest_{timestamp}.json"
        filepath  = os.path.join(self.cache_dir, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            logger.info("[InfraCollector] Manifest saved → %s", filepath)
        except OSError as exc:
            logger.error("[InfraCollector] Cannot save manifest: %s", exc)
            return ""
        return filepath

    # ─────────────────────────────────────────────────────────────────────────
    # Output builder
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_manifest(raw_query: str, artifacts: list[dict]) -> dict:
        """Збирає фінальний маніфест відповідно до формату ТЗ."""
        hot_count  = sum(1 for a in artifacts if a.get("status") == "HOT")
        cold_count = sum(1 for a in artifacts if a.get("status") == "COLD")
        return {
            "raw_query":      raw_query,
            "execution_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "statistics": {
                "total_targets": len(artifacts),
                "hot_signals":   hot_count,
                "cold_baseline": cold_count,
            },
            "artifacts": artifacts,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # HTML utility
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _strip_html(html: str) -> str:
        """
        Видаляє HTML-теги, <script>, <style> та зайві пробіли.
        Повертає чистий текстовий контент сторінки.
        """
        # Видалення блоків script та style разом з вмістом
        text = re.sub(
            r"<(script|style)[^>]*>.*?</(script|style)>",
            " ", html, flags=re.IGNORECASE | re.DOTALL,
        )
        # Видалення решти тегів
        text = re.sub(r"<[^>]+>", " ", text)
        # Нормалізація пробілів
        text = re.sub(r"\s+", " ", text)
        return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Smoke-test (python infra_collector.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from unittest.mock import MagicMock, patch

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── Мок BrightDataClient ─────────────────────────────────────────────────
    FAKE_HTML_HOT = """
    <html><head><title>Держзакупівлі</title></head>
    <body>
      <h1>Тендер №2024-UA-0991</h1>
      <p>Замовлення на постачання сталі 3000 тонн. Термін: 30 днів.</p>
      <p>Ціна: 45 000 000 грн. Виконавець: Метінвест.</p>
      <table><tr><td>Лот</td><td>Кількість</td></tr>
             <tr><td>Сталь Ст3</td><td>3000 т</td></tr></table>
    </body></html>
    """ * 5   # × 5 щоб пройти поріг MIN_CONTENT_CHARS

    FAKE_HTML_CAPTCHA = """
    <html><body>
      <h1>Checking your browser before accessing zakupki.gov.ru</h1>
      <p>DDoS-Guard protection. Please wait...</p>
    </body></html>
    """

    mock_bd = MagicMock(spec=BrightDataClient)

    def _fake_fetch(url, zone="residential", country_iso=None):
        if "captcha" in url:
            return FAKE_HTML_CAPTCHA
        if "empty" in url:
            return ""
        return FAKE_HTML_HOT

    mock_bd.fetch_html_via_proxy.side_effect = _fake_fetch

    # ── Тестова ActionProgram ─────────────────────────────────────────────────
    test_program = {
        "raw_query": "Аналіз тендерів ВПК та логістики Росії 2024",
        "search_tasks": [
            {
                "search_type": "SPATIAL_INFRA",
                "bright_data_tool": "Web_Unlocker",
                "priority": 1,
                "initial_queries": [
                    "https://zakupki.gov.ru/epz/order/notice/lot-info.html?id=991",
                    "https://zakupki.gov.ru/captcha-blocked-page",   # CAPTCHA
                    "https://empty-portal.ru/tenders",                # порожня
                ],
                "target_domains": ["MILITARY_SECURITY"],
            },
            {
                "search_type": "QUANTITATIVE",
                "bright_data_tool": "Web_Scraper_API",
                "priority": 2,
                "initial_queries": [
                    "https://vpk-factory.ru/vacancies/engineer",
                    "site:vpk.ru filetype:pdf звіт",   # dork — пропускається
                ],
                "target_domains": ["ECONOMIC"],
            },
            {
                "search_type": "SEMANTIC",          # Ігнорується цим колектором
                "bright_data_tool": "SERP_API",
                "priority": 3,
                "initial_queries": ["Russian defense news 2024"],
                "target_domains": ["SOCIO_POLITICAL"],
            },
        ],
    }

    collector = InfraCollector(
        bd_client=mock_bd,
        cache_dir="/tmp/infra_cache_test",
    )

    manifest = collector.collect_infra_pipeline(
        action_program=test_program,
        zone="residential",
        country_iso="RU",
        save_manifest=True,
    )

    print("\n" + "=" * 60)
    print("INFRA COLLECTOR — SMOKE TEST OUTPUT")
    print("=" * 60)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

    stats = manifest["statistics"]
    print(f"\n✅ Total targets  : {stats['total_targets']}")
    print(f"   HOT signals   : {stats['hot_signals']}")
    print(f"   COLD baseline : {stats['cold_baseline']}")
    print(f"   Manifest file : {manifest.get('manifest_file', 'not saved')}")

    print("\n── Second run (baseline comparison) ──")
    manifest2 = collector.collect_infra_pipeline(
        action_program=test_program,
        save_manifest=False,
    )
    stats2 = manifest2["statistics"]
    print(f"   HOT (should be 0 if HTML unchanged) : {stats2['hot_signals']}")
    print(f"   COLD (should match total valid)      : {stats2['cold_baseline']}")
