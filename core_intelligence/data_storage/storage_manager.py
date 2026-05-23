#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 3 — Data Persistence & Cache Infrastructure
Path: core_intelligence/data_storage/storage_manager.py
Line Length Limit: 100 characters

Manages structured filesystem storage for raw HTML dumps and semantic JSON SERP data.
"""

import os
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Union

logger = logging.getLogger(__name__)


class StorageManager:
    """Уніфікований менеджер збереження та структурування сирих OSINT-даних у кеші."""

    def __init__(self, base_state_dir: str = "/home/ubuntu/IT-PROJECTS/REILLY/state"):
        self.base_dir = base_state_dir
        # Твої 3 головні інфраструктурні коридори для Блоку №3
        self.categories = {
            "semantic": os.path.join(self.base_dir, "semantic_cache"),
            "infra": os.path.join(self.base_dir, "infra_cache"),
            "quantitative": os.path.join(self.base_dir, "quantitative_cache")
        }
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Перевіряє та автоматично створює необхідну структуру папок на сервері."""
        for path in self.categories.values():
            os.makedirs(path, exist_ok=True)

    def _generate_file_name(self, identifier: str, extension: str) -> str:
        """Генерує детерміноване ім'я файлу на основі MD5-хешу від URL чи Dork-запиту."""
        hash_object = hashlib.md5(identifier.encode("utf-8"))
        hex_dig = hash_object.hexdigest()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{hex_dig}_{timestamp}.{extension}"

    def save_payload(self, category: str, identifier: str, payload: Union[str, Dict[str, Any]]) -> str:
        """
        Записує сирі дані у відповідну папку кешу.
        Повертає абсолютний шлях до створеного файлу.
        """
        if category not in self.categories:
            logger.error(f"Rejected illegal storage channel category: {category}")
            raise ValueError(f"Unknown storage category channel: {category}")

        target_dir = self.categories[category]
        
        # Визначаємо розширення залежно від типу даних
        is_dict = isinstance(payload, dict)
        ext = "json" if is_dict else "html"
        
        file_name = self._generate_file_name(identifier, ext)
        full_path = os.path.join(target_dir, file_name)

        try:
            if is_dict:
                with open(full_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            else:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(str(payload))
            
            logger.info(f"Successfully cached raw payload to {full_path}")
            return full_path

        except IOError as e:
            logger.error(f"Critical I/O failure while writing to storage: {e}")
            raise e


# --- Швидкий локальний тест модуля ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = StorageManager()
    
    # Тест 1: Збереження семантичного JSON (наприклад, видача Google)
    test_json = {"query": "site:gov.ua target", "results_count": 42}
    path_json = manager.save_payload("semantic", "site:gov.ua target", test_json)
    print(f"JSON збережено в: {path_json}")

    # Тест 2: Збереження сирого HTML (інфраструктурний зріз сайту)
    test_html = "<html><body><h1>Reilly Target Page</h1></body></html>"
    path_html = manager.save_payload("infra", "https://target-site.com/about", test_html)
    print(f"HTML збережено в: {path_html}")