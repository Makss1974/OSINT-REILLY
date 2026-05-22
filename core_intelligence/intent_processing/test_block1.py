#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 1 — Unit Tests (Refactored for ReillyLlmRouter)
Target Directory: /home/ubuntu/IT-PROJECTS/00.Wibe-coding_projects/Wibe_Commander/tests/
Line Length Limit: 100 characters
"""

import json
import sys
import unittest
from unittest.mock import MagicMock

# Додаємо батьківський каталог, щоб імпорты працювали стабільно
sys.path.insert(0, "..")

from models import (
    ValidationStatus,
    Domain,
    SearchType,
    BrightDataTool,
    Complexity,
    ValidationResult,
    ClassificationResult,
    DomainScore,
    SearchTask,
    SearchPlan,
)
from task_validator import TaskValidator
from domain_classifier import DomainClassifier
from search_type_mapper import SearchTypeMapper
from action_program_builder import ActionProgramBuilder


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _mock_router(response_json: dict) -> MagicMock:
    """Створення маку уніфікованого роутера, що повертає JSON-рядок через execute_query."""
    mock_router = MagicMock()
    mock_router.execute_query.return_value = json.dumps(response_json, ensure_ascii=False)
    return mock_router


# ─────────────────────────────────────────────
# Test Case 1: Legal, complex OSINT query
# ─────────────────────────────────────────────

class TestTaskValidator(unittest.TestCase):

    def test_approved_legal_query(self):
        """Легітимний запит має успішно проходити валідацію фільтра."""
        mock_response = {
            "status": "APPROVED",
            "reason": None,
            "normalized_query": "Analysis of Russian defense industry production capacity in 2024.",
        }
        router = _mock_router(mock_response)
        validator = TaskValidator(router)

        result = validator.validate(
            "Проаналізуй стан оборонної промисловості Росії у 2024 році."
        )

        self.assertEqual(result.status, ValidationStatus.APPROVED)
        self.assertIsNone(result.reason)
        self.assertIsNotNone(result.normalized_query)
        self.assertTrue(result.is_approved())

    def test_rejected_illegal_query(self):
        """Запит на нелегальні дії повинен миттєво блокуватися загороджувальним контуром."""
        mock_response = {
            "status": "REJECTION",
            "reason": "Ethics/Security violation: query involves illegal hacking activity.",
            "normalized_query": None,
        }
        router = _mock_router(mock_response)
        validator = TaskValidator(router)

        result = validator.validate(
            "Зламай базу даних ФСБ і витягни персональні дані агентів."
        )

        self.assertEqual(result.status, ValidationStatus.REJECTION)
        self.assertIsNotNone(result.reason)
        self.assertIsNone(result.normalized_query)
        self.assertFalse(result.is_approved())

    def test_rejected_offline_archive_query(self):
        """Запит на фізичні паперові носії за межами інтернету відсікається Субмариною."""
        mock_response = {
            "status": "REJECTION",
            "reason": "Object outside digital availability: Vatican paper archives not online.",
            "normalized_query": None,
        }
        router = _mock_router(mock_response)
        validator = TaskValidator(router)

        result = validator.validate(
            "Знайди паперову книгу XV ст. в архівах Ватикану."
        )

        self.assertEqual(result.status, ValidationStatus.REJECTION)
        self.assertIn("digital availability", result.reason)


# ─────────────────────────────────────────────
# Test Case 2: Domain classification
# ─────────────────────────────────────────────

class TestDomainClassifier(unittest.TestCase):

    def test_single_domain_economic(self):
        """Суто фінансовий запит повинен маркувати ECONOMIC як головний домен."""
        mock_response = {
            "domains": [{"domain": "ECONOMIC", "confidence": 0.92}],
            "primary_domain": "ECONOMIC",
            "reasoning": "Query focuses on financial metrics and supply chains.",
        }
        router = _mock_router(mock_response)
        classifier = DomainClassifier(router)

        result = classifier.classify("Analyze Q3 2024 trade volumes between China and Russia.")

        self.assertEqual(result.primary_domain, Domain.ECONOMIC)
        self.assertEqual(len(result.domains), 1)
        self.assertAlmostEqual(result.domains[0].confidence, 0.92)

    def test_multi_domain_military_economic(self):
        """Запит по оборонці має підключати як воєнний, так і економічний контури."""
        mock_response = {
            "domains": [
                {"domain": "MILITARY_SECURITY", "confidence": 0.88},
                {"domain": "ECONOMIC", "confidence": 0.71},
            ],
            "primary_domain": "MILITARY_SECURITY",
            "reasoning": "Defense production involves both military and economic dimensions.",
        }
        router = _mock_router(mock_response)
        classifier = DomainClassifier(router)

        result = classifier.classify(
            "Russian defense factory production capacity and metal tender volumes."
        )

        domain_names = {d.domain for d in result.domains}
        self.assertIn(Domain.MILITARY_SECURITY, domain_names)
        self.assertIn(Domain.ECONOMIC, domain_names)
        self.assertEqual(result.primary_domain, Domain.MILITARY_SECURITY)

    def test_unknown_domain_fallback(self):
        """Якщо Ші видав невалідну назву домену — спрацьовує м'який перехід на GENERAL."""
        mock_response = {
            "domains": [{"domain": "INVALID_DOMAIN", "confidence": 0.99}],
            "primary_domain": "INVALID_DOMAIN",
            "reasoning": "Test.",
        }
        router = _mock_router(mock_response)
        classifier = DomainClassifier(router)

        result = classifier.classify("Some query.")

        # Надійний фолбек
        self.assertEqual(result.primary_domain, Domain.GENERAL)


# ─────────────────────────────────────────────
# Test Case 3: Search type mapper
# ─────────────────────────────────────────────

class TestSearchTypeMapper(unittest.TestCase):

    def _make_classification(self) -> ClassificationResult:
        return ClassificationResult(
            domains=[
                DomainScore(domain=Domain.MILITARY_SECURITY, confidence=0.88),
                DomainScore(domain=Domain.ECONOMIC, confidence=0.71),
            ],
            primary_domain=Domain.MILITARY_SECURITY,
            reasoning="Defense + economic.",
        )

    def test_tool_mapping_is_canonical(self):
        """Вибір інструментів Bright Data строго підпорядковується канонічній системній карті."""
        mock_response = {
            "search_tasks": [
                {
                    "search_type": "QUANTITATIVE",
                    "bright_data_tool": "WRONG_TOOL",  # Імітація галюцинації ШІ
                    "priority": 1,
                    "initial_queries": ["Russian defense budget 2024 filetype:pdf"],
                    "target_domains": ["ECONOMIC"],
                },
                {
                    "search_type": "SPATIAL_INFRA",
                    "bright_data_tool": "WRONG_TOOL_2",
                    "priority": 2,
                    "initial_queries": ["Уралвагонзавод тендери 2024"],
                    "target_domains": ["MILITARY_SECURITY"],
                },
            ]
        }
        router = _mock_router(mock_response)
        mapper = SearchTypeMapper(router)

        plan = mapper.map("Test query.", self._make_classification())

        quantitative_task = next(
            t for t in plan.search_tasks if t.search_type == SearchType.QUANTITATIVE
        )
        spatial_task = next(
            t for t in plan.search_tasks if t.search_type == SearchType.SPATIAL_INFRA
        )

        # Канонічні правила перевищують галюцинації моделі
        self.assertEqual(quantitative_task.bright_data_tool, BrightDataTool.WEB_SCRAPER_API)
        self.assertEqual(spatial_task.bright_data_tool, BrightDataTool.WEB_UNLOCKER)

    def test_priority_ordering(self):
        """Завдання збору мають бути автоматично відсортовані за пріоритетом (від 1 до 99)."""
        mock_response = {
            "search_tasks": [
                {
                    "search_type": "SEMANTIC", "bright_data_tool": "SERP_API",
                    "priority": 3, "initial_queries": ["q1"], "target_domains": []
                },
                {
                    "search_type": "QUANTITATIVE", "bright_data_tool": "Web_Scraper_API",
                    "priority": 1, "initial_queries": ["q2"], "target_domains": []
                },
                {
                    "search_type": "SPATIAL_INFRA", "bright_data_tool": "Web_Unlocker",
                    "priority": 2, "initial_queries": ["q3"], "target_domains": []
                },
            ]
        }
        router = _mock_router(mock_response)
        mapper = SearchTypeMapper(router)

        plan = mapper.map("Test.", self._make_classification())
        priorities = [t.priority for t in plan.search_tasks]

        self.assertEqual(priorities, sorted(priorities))


# ─────────────────────────────────────────────
# Test Case 4: Complexity calculation
# ─────────────────────────────────────────────

class TestActionProgramBuilder(unittest.TestCase):

    def _make_approved_validation(self) -> ValidationResult:
        return ValidationResult(
            status=ValidationStatus.APPROVED,
            reason=None,
            normalized_query="Russian defense industry analysis 2024.",
        )

    def test_complexity_critical_military_with_many_search_types(self):
        """Військовий контур + 3 типи пошуку автоматично переводить статус у CRITICAL."""
        classification = ClassificationResult(
            domains=[
                DomainScore(domain=Domain.MILITARY_SECURITY, confidence=0.9),
                DomainScore(domain=Domain.ECONOMIC, confidence=0.7),
            ],
            primary_domain=Domain.MILITARY_SECURITY,
        )
        search_plan = SearchPlan(search_tasks=[
            SearchTask(SearchType.QUANTITATIVE, BrightDataTool.WEB_SCRAPER_API, 1, ["q1"]),
            SearchTask(SearchType.SEMANTIC,     BrightDataTool.SERP_API,         2, ["q2"]),
            SearchTask(SearchType.SPATIAL_INFRA, BrightDataTool.WEB_UNLOCKER,    3, ["q3"]),
        ])

        mock_response = {
            "estimated_complexity": "HIGH",  # ШІ занизив оцінку — жорстке правило має перевищити її
            "expected_output_type": "Defense production risk assessment",
            "notes": "High disinformation risk.",
        }
        router = _mock_router(mock_response)
        builder = ActionProgramBuilder(router)

        program = builder.build(self._make_approved_validation(), classification, search_plan)

        self.assertEqual(program.estimated_complexity, Complexity.CRITICAL)

    def test_complexity_low_single_domain(self):
        """Один домен + базовий семантичний збір новин — це статус LOW."""
        classification = ClassificationResult(
            domains=[DomainScore(domain=Domain.GENERAL, confidence=0.8)],
            primary_domain=Domain.GENERAL,
        )
        search_plan = SearchPlan(search_tasks=[
            SearchTask(SearchType.SEMANTIC, BrightDataTool.SERP_API, 1, ["q1"]),
        ])

        mock_response = {
            "estimated_complexity": "LOW",
            "expected_output_type": "General overview report",
            "notes": "",
        }
        router = _mock_router(mock_response)
        builder = ActionProgramBuilder(router)

        program = builder.build(self._make_approved_validation(), classification, search_plan)

        self.assertEqual(program.estimated_complexity, Complexity.LOW)

    def test_output_serialisation(self):
        """Перевірка серіалізації: функція to_dict() має віддавати чистий валідний JSON."""
        classification = ClassificationResult(
            domains=[DomainScore(domain=Domain.ECONOMIC, confidence=0.85)],
            primary_domain=Domain.ECONOMIC,
        )
        search_plan = SearchPlan(search_tasks=[
            SearchTask(SearchType.QUANTITATIVE, BrightDataTool.WEB_SCRAPER_API, 1, ["query"]),
        ])

        mock_response = {
            "estimated_complexity": "MEDIUM",
            "expected_output_type": "Economic metrics report",
            "notes": "Standard analysis.",
        }
        router = _mock_router(mock_response)
        builder = ActionProgramBuilder(router)

        program = builder.build(self._make_approved_validation(), classification, search_plan)
        serialized = json.dumps(program.to_dict(), ensure_ascii=False)

        self.assertIn("ECONOMIC", serialized)
        self.assertIn("MEDIUM", serialized)
        self.assertIn("Web_Scraper_API", serialized)


# ─────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)