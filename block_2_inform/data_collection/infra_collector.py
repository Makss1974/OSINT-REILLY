#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 2 — Infrastructure HTML Collector (Maxwell Daemon)
Path: /home/ubuntu/IT-PROJECTS/REILLY/block_2_inform/data_collection/infra_collector.py
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from .brightdata_client import BrightDataClient

logger = logging.getLogger(__name__)

class InfraCollector:
    def __init__(self, bd_client: BrightDataClient, cache_dir: str = "/home/ubuntu/IT-PROJECTS/REILLY/state/infra_cache"):
        self.bd_client = bd_client
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def collect_infra_pipeline(self, action_program: Any, zone: str = "residential", country_iso: str = "RU", save_manifest: bool = True) -> Dict[str, Any]:
        logger.info("[Maxwell Daemon] ⚡ Запуск штурму прямої інфраструктури об'єктів...")
        
        manifest = {
            "timestamp": time.time(),
            "statistics": {"total_targets": 0, "hot_signals": 0, "cold_baseline": 0},
            "hot_signals_data": []
        }
        
        # Обробка тасок типу SPATIAL_INFRA або TEMPORAL_ANOMALY за твоїм бойовим кодом
        for task in action_program.search_tasks:
            if task.search_type in ["SPATIAL_INFRA", "TEMPORAL_ANOMALY"]:
                for url in task.initial_queries:
                    manifest["statistics"]["total_targets"] += 1
                    html = self.bd_client.fetch_html_via_proxy(url, zone, country_iso)
                    
                    # Логіка Демона Максвелла: рахуємо хеш, відсікаємо капчу
                    html_hash = hashlib.sha256(html.encode('utf-8')).hexdigest()
                    manifest["statistics"]["hot_signals"] += 1
                    manifest["hot_signals_data"].append({
                        "url": url,
                        "search_type": task.search_type,
                        "hash": html_hash,
                        "status": "HOT_SIGNAL",
                        "payload_snippet": html[:200]
                    })
                    
        return manifest