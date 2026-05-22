#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 3 — Data Persistence & Cache Infrastructure
Path: core_intelligence/data_storage/storage_manager.py
Line Length Limit: 100 characters

Roles:
  - Isolates three data streams into dedicated cache corridors.
  - Generates deterministic, collision-resistant filenames via MD5(identifier).
  - Prevents duplicate writes: identical hash + identical size → STORAGE_SKIPPED_EXISTING.
  - Returns a structured StorageResult on every operation for full auditability.

Integration contract:
  CALLED BY ← SemanticCollector, InfraCollector (Block 2)
  CALLED BY ← AnalyticsEngine              (Block 4, quantitative data)
  OUTPUT    → Absolute file path + operation status for manifest records
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Valid storage categories and their subdirectory names
CATEGORIES: Dict[str, str] = {
    "semantic":     "semantic_cache",      # SERP results, dorks, text slices
    "infra":        "infra_cache",          # Raw HTML from proxy sweeps
    "quantitative": "quantitative_cache",  # Tables, CSV, structured numeric data
}

# Operation status codes returned in StorageResult
STATUS_WRITTEN          = "STORAGE_WRITTEN"
STATUS_SKIPPED_EXISTING = "STORAGE_SKIPPED_EXISTING"
STATUS_OVERWRITTEN      = "STORAGE_OVERWRITTEN"
STATUS_FAILED           = "STORAGE_FAILED"


# ─────────────────────────────────────────────────────────────────────────────
# StorageResult — structured return value for every save operation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StorageResult:
    """
    Повний звіт про операцію збереження для аудиту та ведення маніфесту.

    Attributes:
        status:      Код результату (STORAGE_WRITTEN / SKIPPED / FAILED).
        filepath:    Абсолютний шлях до файлу (порожній при FAILED).
        category:    Категорія сховища ("semantic"|"infra"|"quantitative").
        identifier:  Вхідний ідентифікатор (URL або рядок дорку).
        file_hash:   MD5 від identifier — детерміністичний ключ файлу.
        size_bytes:  Розмір записаного файлу в байтах (0 якщо не записано).
        skipped:     True якщо файл уже існував і мав ідентичний розмір.
        error:       Текст помилки при STATUS_FAILED, інакше None.
    """
    status:     str
    filepath:   str
    category:   str
    identifier: str
    file_hash:  str
    size_bytes: int  = 0
    skipped:    bool = False
    error:      Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status":     self.status,
            "filepath":   self.filepath,
            "category":   self.category,
            "identifier": self.identifier,
            "file_hash":  self.file_hash,
            "size_bytes": self.size_bytes,
            "skipped":    self.skipped,
            "error":      self.error,
        }


# ─────────────────────────────────────────────────────────────────────────────
# StorageManager
# ─────────────────────────────────────────────────────────────────────────────

class StorageManager:
    """
    Уніфікований менеджер збереження та структурування сирих OSINT-даних.

    Три ізольовані коридори:
      semantic/     ← SemanticCollector  (SERP JSON, дорки)
      infra/        ← InfraCollector     (сирий HTML)
      quantitative/ ← AnalyticsEngine    (CSV, таблиці, числові масиви)

    Детерміноване іменування: MD5(identifier) + UTC-timestamp + розширення.
    Захист від дублювання: однаковий хеш + однаковий розмір → SKIPPED.
    """

    def __init__(
        self,
        base_state_dir: str = "/home/ubuntu/IT-PROJECTS/REILLY/state",
    ):
        """
        Args:
            base_state_dir: Базова директорія стану системи.
                            Усі підпапки кешу будуть створені всередині неї.
        """
        self.base_dir   = base_state_dir
        self.cache_dirs = {
            cat: os.path.join(base_state_dir, subdir)
            for cat, subdir in CATEGORIES.items()
        }
        self._ensure_directories()
        logger.info(
            "[StorageManager] Initialized | base=%s | corridors=%s",
            base_state_dir,
            list(self.cache_dirs.keys()),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def save_raw_payload(
        self,
        category: str,
        identifier: str,
        payload: Union[str, Dict[str, Any]],
        overwrite: bool = False,
    ) -> StorageResult:
        """
        Записує сирі дані у відповідний інфраструктурний коридор сховища.

        Args:
            category:   Коридор сховища: "semantic" | "infra" | "quantitative".
            identifier: URL сайту або текст дорку — ключ для MD5-хешування.
            payload:    Дані для запису. dict → .json, str → .html або .txt.
            overwrite:  Якщо True — перезаписати навіть при збігу розміру.

        Returns:
            StorageResult з повним аудитним слідом операції.
        """
        # ── Валідація категорії ───────────────────────────────────────────────
        if category not in self.cache_dirs:
            msg = (
                f"Unknown storage category: '{category}'. "
                f"Valid: {list(self.cache_dirs.keys())}"
            )
            logger.error("[StorageManager] %s", msg)
            return StorageResult(
                status=STATUS_FAILED, filepath="", category=category,
                identifier=identifier, file_hash="", error=msg,
            )

        # ── Генерація детермінованого імені файлу ────────────────────────────
        file_hash = self._md5(identifier)
        extension = self._detect_extension(payload)
        filename  = self._generate_filename(file_hash, extension)
        filepath  = os.path.join(self.cache_dirs[category], filename)

        # ── Серіалізація payload у байти (UTF-8) ─────────────────────────────
        try:
            raw_str   = self._serialize(payload, extension)
            raw_bytes = raw_str.encode("utf-8")   # байти — єдиний еталон розміру
        except (TypeError, ValueError, UnicodeEncodeError) as exc:
            msg = f"Serialization error: {exc}"
            logger.error("[StorageManager] %s | identifier=%.60s", msg, identifier)
            return StorageResult(
                status=STATUS_FAILED, filepath="", category=category,
                identifier=identifier, file_hash=file_hash, error=msg,
            )

        incoming_size = len(raw_bytes)   # байти, а не символи — точна відповідність getsize()

        # ── Захист від дублювання ────────────────────────────────────────────
        # Шукаємо будь-який файл із тим самим MD5-префіксом у коридорі.
        # Timestamp у назві змінюється між сесіями, тому порівнюємо лише хеш.
        if not overwrite:
            existing = self._find_existing(category, file_hash)
            if existing:
                existing_size = os.path.getsize(existing)
                if existing_size == incoming_size:
                    logger.info(
                        "[StorageManager] SKIPPED (hash match + size %d B) → %s",
                        incoming_size, os.path.basename(existing),
                    )
                    return StorageResult(
                        status=STATUS_SKIPPED_EXISTING,
                        filepath=existing,
                        category=category,
                        identifier=identifier,
                        file_hash=file_hash,
                        size_bytes=existing_size,
                        skipped=True,
                    )
                # Той самий хеш, але розмір відрізняється — оновлення контенту
                logger.info(
                    "[StorageManager] Hash match but size delta (%d→%d B) "
                    "— overwriting: %s",
                    existing_size, incoming_size, os.path.basename(existing),
                )
                filepath = existing   # Перезаписуємо існуючий файл

        # ── Запис на диск (binary mode — гарантує точний розмір) ────────────
        try:
            with open(filepath, "wb") as f:
                f.write(raw_bytes)

            written_size = os.path.getsize(filepath)
            logger.info(
                "[StorageManager] %s | %d B → %s",
                STATUS_WRITTEN, written_size, os.path.basename(filepath),
            )
            return StorageResult(
                status=STATUS_WRITTEN,
                filepath=filepath,
                category=category,
                identifier=identifier,
                file_hash=file_hash,
                size_bytes=written_size,
            )

        except OSError as exc:
            msg = f"Disk write error: {exc}"
            logger.error(
                "[StorageManager] FAILED | %s | path=%s", msg, filepath
            )
            return StorageResult(
                status=STATUS_FAILED, filepath="", category=category,
                identifier=identifier, file_hash=file_hash, error=msg,
            )

    def list_cache(
        self,
        category: str,
        limit: int = 50,
    ) -> list[Dict[str, Any]]:
        """
        Повертає список файлів у вказаному коридорі сховища.

        Args:
            category: Коридор ("semantic"|"infra"|"quantitative").
            limit:    Максимальна кількість записів (сортування за часом — новіші першими).

        Returns:
            Список словників: {filename, filepath, size_bytes, modified_utc}
        """
        if category not in self.cache_dirs:
            logger.warning("[StorageManager] list_cache: unknown category %s", category)
            return []

        cache_path = self.cache_dirs[category]
        try:
            entries = []
            for fname in os.listdir(cache_path):
                fpath = os.path.join(cache_path, fname)
                if not os.path.isfile(fpath):
                    continue
                mtime = os.path.getmtime(fpath)
                entries.append({
                    "filename":     fname,
                    "filepath":     fpath,
                    "size_bytes":   os.path.getsize(fpath),
                    "modified_utc": datetime.fromtimestamp(
                        mtime, tz=timezone.utc
                    ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                })
            entries.sort(key=lambda x: x["modified_utc"], reverse=True)
            return entries[:limit]
        except OSError as exc:
            logger.error("[StorageManager] list_cache error: %s", exc)
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        Повертає статистику по всіх трьох коридорах сховища.

        Returns:
            {category: {file_count, total_size_bytes, total_size_kb}}
        """
        stats: Dict[str, Any] = {}
        for cat, path in self.cache_dirs.items():
            try:
                files = [
                    f for f in os.listdir(path)
                    if os.path.isfile(os.path.join(path, f))
                ]
                total_bytes = sum(
                    os.path.getsize(os.path.join(path, f)) for f in files
                )
                stats[cat] = {
                    "file_count":       len(files),
                    "total_size_bytes": total_bytes,
                    "total_size_kb":    round(total_bytes / 1024, 2),
                }
            except OSError as exc:
                stats[cat] = {"error": str(exc)}
        return stats

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _ensure_directories(self) -> None:
        """Перевіряє та створює необхідну структуру папок."""
        for path in self.cache_dirs.values():
            os.makedirs(path, exist_ok=True)
            logger.debug("[StorageManager] Directory ensured: %s", path)

    def _find_existing(self, category: str, file_hash: str) -> Optional[str]:
        """
        Шукає файл із вказаним MD5-хешем у коридорі сховища.
        Повертає абсолютний шлях якщо знайдено, інакше None.
        Порівняння за префіксом імені: <md5hash>_*.ext
        """
        cache_path = self.cache_dirs[category]
        try:
            for fname in os.listdir(cache_path):
                if fname.startswith(file_hash + "_"):
                    return os.path.join(cache_path, fname)
        except OSError:
            pass
        return None

    @staticmethod
    def _md5(text: str) -> str:
        """Обчислює MD5-хеш від рядка-ідентифікатора."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _generate_filename(file_hash: str, extension: str) -> str:
        """
        Генерує детерміноване ім'я файлу: MD5_hash + UTC-timestamp + розширення.
        MD5 гарантує детермінізм; timestamp унеможливлює колізії між сесіями.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{file_hash}_{timestamp}.{extension}"

    @staticmethod
    def _detect_extension(payload: Union[str, Dict[str, Any]]) -> str:
        """
        Визначає розширення файлу за типом payload:
          dict          → .json  (структуровані дані SERP, маніфести)
          str з '<html' → .html  (сирий HTML з InfraCollector)
          str решта     → .txt   (текстові фрагменти, дорки)
        """
        if isinstance(payload, dict):
            return "json"
        if isinstance(payload, str) and "<html" in payload.lower()[:200]:
            return "html"
        return "txt"

    @staticmethod
    def _serialize(
        payload: Union[str, Dict[str, Any]],
        extension: str,
    ) -> Union[str, bytes]:
        """
        Серіалізує payload у відповідний формат для запису на диск.
        JSON отримує indent=2 та ensure_ascii=False для зручного аудиту.
        HTML та TXT зберігаються як є.
        """
        if extension == "json":
            if isinstance(payload, dict):
                return json.dumps(payload, ensure_ascii=False, indent=2)
            # Рядок, що виглядає як JSON — перевіряємо і форматуємо
            try:
                parsed = json.loads(payload)
                return json.dumps(parsed, ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, TypeError):
                return str(payload)
        return str(payload) if not isinstance(payload, str) else payload


# ─────────────────────────────────────────────────────────────────────────────
# Smoke-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import shutil
    import tempfile

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    tmp_dir = tempfile.mkdtemp(prefix="reilly_storage_test_")
    print(f"\n=== StorageManager Smoke Test | base={tmp_dir} ===\n")

    sm = StorageManager(base_state_dir=tmp_dir)

    # ── Test 1: збереження JSON (semantic) ───────────────────────────────────
    serp_payload = {
        "query": 'site:gov.ru "тендер" "Уралвагонзавод" 2024',
        "results": [{"title": "Тендер №991", "url": "https://zakupki.gov.ru/991"}],
    }
    r1 = sm.save_raw_payload(
        category="semantic",
        identifier='site:gov.ru "тендер" "Уралвагонзавод" 2024',
        payload=serp_payload,
    )
    assert r1.status == STATUS_WRITTEN
    assert r1.filepath.endswith(".json")
    assert r1.size_bytes > 0
    print(f"Test 1 PASS | JSON written | {r1.size_bytes} B → {os.path.basename(r1.filepath)}")

    # ── Test 2: захист від дублювання (same hash + same size) ────────────────
    r2 = sm.save_raw_payload(
        category="semantic",
        identifier='site:gov.ru "тендер" "Уралвагонзавод" 2024',
        payload=serp_payload,
    )
    assert r2.status == STATUS_SKIPPED_EXISTING
    assert r2.skipped is True
    print(f"Test 2 PASS | Duplicate skipped correctly | status={r2.status}")

    # ── Test 3: збереження HTML (infra) ──────────────────────────────────────
    html_payload = (
        "<html><body><h1>Держзакупівлі</h1>"
        "<p>Тендер на 3000 тонн сталі</p></body></html>"
    )
    r3 = sm.save_raw_payload(
        category="infra",
        identifier="https://zakupki.gov.ru/order/991",
        payload=html_payload,
    )
    assert r3.status == STATUS_WRITTEN
    assert r3.filepath.endswith(".html")
    print(f"Test 3 PASS | HTML written | {r3.size_bytes} B → {os.path.basename(r3.filepath)}")

    # ── Test 4: збереження CSV-рядка (quantitative) ───────────────────────────
    csv_payload = "date,product,volume_tons\n2024-01-15,Сталь Ст3,3000\n2024-02-01,Алюміній,500"
    r4 = sm.save_raw_payload(
        category="quantitative",
        identifier="customs_data_saratov_2024",
        payload=csv_payload,
    )
    assert r4.status == STATUS_WRITTEN
    assert r4.filepath.endswith(".txt")
    print(f"Test 4 PASS | TXT written  | {r4.size_bytes} B → {os.path.basename(r4.filepath)}")

    # ── Test 5: невідома категорія → структурована помилка ───────────────────
    r5 = sm.save_raw_payload(
        category="unknown_corridor",
        identifier="test",
        payload="data",
    )
    assert r5.status == STATUS_FAILED
    assert r5.error is not None
    print(f"Test 5 PASS | Invalid category rejected | error: {r5.error[:55]}")

    # ── Test 6: list_cache та get_stats ──────────────────────────────────────
    listing = sm.list_cache("semantic")
    assert len(listing) == 1
    stats = sm.get_stats()
    assert stats["semantic"]["file_count"] == 1
    assert stats["infra"]["file_count"] == 1
    assert stats["quantitative"]["file_count"] == 1
    print(
        f"Test 6 PASS | list_cache={len(listing)} | "
        f"stats: sem={stats['semantic']['file_count']} "
        f"inf={stats['infra']['file_count']} "
        f"qty={stats['quantitative']['file_count']}"
    )

    # ── Test 7: MD5 детермінізм — той самий identifier → той самий hash ──────
    h1 = StorageManager._md5("https://zakupki.gov.ru/order/991")
    h2 = StorageManager._md5("https://zakupki.gov.ru/order/991")
    assert h1 == h2
    print(f"Test 7 PASS | MD5 determinism confirmed | hash={h1}")

    shutil.rmtree(tmp_dir)
    print(f"\n✅ ALL 7 TESTS PASSED — StorageManager is battle-ready.\n")
