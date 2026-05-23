#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 2 — Semantic Counter-Collector (Red Teaming)
Path: /home/ubuntu/IT-PROJECTS/REILLY/block_2_inform/data_collection/semantic_collector.py
"""

import json
import logging
import os
import time
from typing import Optional, Dict, Any
from .brightdata_client import BrightDataClient

logger = logging.getLogger(__name__)

class SemanticCollector:
    def __init__(self, bd_client: BrightDataClient, router: Any = None, cache_dir: str = "/home/ubuntu/IT-PROJECTS/REILLY/state/semantic_cache"):
        self.bd_client = bd_client
        self.router = router
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def collect_semantic_pipeline(self, action_program: Any, country: str = "ru", language: str = "ru", save_cache: bool = True) -> Dict[str, Any]:
        logger.info("[Semantic Sweep] 🧠 Запуск подвійного семантичного контуру (Аргументи ЗА/ПРОТИ)...")
        
        result_package = {
            "timestamp": time.time(),
            "semantic_data": []
        }
        
        for task in action_program.search_tasks:
            if task.search_type in ["SEMANTIC", "LINGUISTIC_STRESS", "CORRELATION_CROSS"]:
                serp_raw = self.bd_client.fetch_serp(task.initial_queries, country, language)
                result_package["semantic_data"].append({
                    "search_type": task.search_type,
                    "instruction": task.meta_instruction,
                    "serp_payload": serp_raw
                })
                
        return result_package