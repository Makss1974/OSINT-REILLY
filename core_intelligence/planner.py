#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY: Block #1 - Target & Action Planner (The Submarine Filter)
Path: /home/ubuntu/IT-PROJECTS/00.Wibe-coding_projects/Wibe_Commander/core_intelligence/planner.py
Line Length Limit: 100 characters
"""

import os
import json
import logging

class ReillyPlanner:
    def __init__(self, architecture_path="./docs/architecture.json"):
        self.arch_path = architecture_path
        self.config = self._load_architecture()

    def _load_architecture(self):
        """Завантаження технічних лімітів та правил з json-конфігу."""
        if not os.path.exists(self.arch_path):
            logging.warning("Architecture config not found at %s. Using safe defaults.", 
                            self.arch_path)
            return {}
        try:
            with open(self.arch_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error("Failed to parse architecture JSON: %s", str(e))
            return {}

    def validate_task(self, raw_query: str) -> dict:
        """
        Етап 1.1: Фільтр «Субмарини»
        Перевірка релевантності цифровому середовищу та базовим етичним рамкам розробки.
        """
        query_lower = raw_query.lower()
        
        # Перевірка на технічну недоступність (офлайн/паперові носії)
        offline_markers = ["паперова книга", "паперовий архів", "архів ватикану", "оригінал рукопису"]
        if any(marker in query_lower for marker in offline_markers):
            return {
                "status": "REJECTED",
                "reason": "REJECTION: Object outside digital availability (Offline data constraint)."
            }

        # Етично-безпековий загороджувальний контур
        safety_markers = ["зломати", "пароль від", "медична картка", "синтез наркотиків", "hack"]
        if any(marker in query_lower for marker in safety_markers):
            return {
                "status": "REJECTED",
                "reason": "REJECTION: Security guardrail violation (Prohibited/Confidential domain)."
            }

        return {"status": "APPROVED", "reason": "Query matches OSINT processing capabilities."}

    def classify_domain(self, raw_query: str) -> list:
        """
        Етап 1.2: Класифікація за 6 напрямками
        Визначення доменів ризику для підключення відповідних Радників.
        """
        query_lower = raw_query.lower()
        detected_domains = []

        # Словникові маркери на основі ТЗ
        mapping = {
            "economic_research": ["завод", "підприємство", "ціна", "фрахт", "економіка", "постачання"],
            "socio_political_analysis": ["настрої", "соцмережі", "пропаганда", "змі", "публікації"],
            "scientific_tech_scouting": ["іт", "вакансії", "впк", "технології", "інженер"],
            "military_and_security_threats": ["війна", "загроза", "міст", "порт", "інфраструктура"],
            "ecology_and_life_conditions": ["екологія", "викиди", "ресурси", "вода", "радіація"]
        }

        for domain, markers in mapping.items():
            if any(marker in query_lower for marker in markers):
                detected_domains.append(domain)

        if not detected_domains:
            detected_domains.append("general_monitoring")

        return detected_domains

    def map_search_types(self, domains: list) -> dict:
        """
        Етап 1.3: Визначення Типу інформаційного пошуку
        Прив'язка аналітичних контурів до технічних інструментів Bright Data.
        """
        search_plan = {}

        if "economic_research" in domains:
            search_plan["statistical_quantitative"] = {
                "tool": "Web_Scraper_API",
                "data": "Customs tariffs, supply volumes, financial statements, registries"
            }
        if "socio_political_analysis" in domains or "general_monitoring" in domains:
            search_plan["semantic_discursive"] = {
                "tool": "SERP_API",
                "data": "Press articles, baseline narratives, media monitoring, state news"
            }
        if "military_and_security_threats" in domains or "socio_political_analysis" in domains:
            search_plan["social_listening_local"] = {
                "tool": "Scraping_Browser",
                "data": "Geo-targeted community chats, localized forums, comment sections"
            }
        if "scientific_tech_scouting" in domains or "military_and_security_threats" in domains:
            search_plan["infrastructure_spatial"] = {
                "tool": "Web_Unlocker",
                "data": "State tenders, factory job openings, infrastructure mapping data"
            }

        return search_plan

    def generate_action_plan(self, raw_query: str) -> dict:
        """Головний оркестратор Блоку №1 - формування ТЗ для збирачів."""
        validation = self.validate_task(raw_query)
        if validation["status"] == "REJECTED":
            return {"status": "FAILED", "error": validation["reason"]}

        domains = self.classify_domain(raw_query)
        search_types = self.map_search_types(domains)

        return {
            "status": "SUCCESS",
            "target_query": raw_query,
            "assigned_domains": domains,
            "bright_data_execution_plan": search_types
        }

if __name__ == "__main__":
    # Тестовий запуск для перевірки логіки
    planner = ReillyPlanner()
    test_query = "Аналіз логістики навколо заводу в Саратові та вакансії ВПК"
    plan = planner.generate_action_plan(test_query)
    print(json.dumps(plan, indent=2, ensure_ascii=False))