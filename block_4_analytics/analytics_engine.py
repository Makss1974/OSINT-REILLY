#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 4 — ANALYTICS ENGINE (Головний диспетчер аналітичного контуру)
Path: block_4_analytics/analytics_engine.py
Line Length Limit: 100 characters

Orchestrates 4 core intelligence families: General, Economic, Scientific, and Social.
"""

import logging
import os
import sys
import time
from enum import Enum
from typing import Dict, Any, List, Optional

# Налаштування відносних імпортів для кореня проекту
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core_intelligence.router import ReillyLlmRouter
from block_4_analytics.signal_evaluator import MasterSignalEvaluator

# Імпорт наших 4 нових бойових сімейств методів
from block_4_analytics.family_general import GeneralAnalyticsFamily
from block_4_analytics.family_economic import EconomicAnalyticsFamily
from block_4_analytics.family_scientific import ScientificAnalyticsFamily
from block_4_analytics.family_social import SocialAnalyticsFamily

logger = logging.getLogger(__name__)


class AnalysisLayer(str, Enum):
    GREENE   = "L1_GREENE_ROOT_CAUSE"
    JERVIS   = "L2_JERVIS_SIGNAL_DISC"
    GOLDRATT = "L3_GOLDRATT_BOTTLENECK"
    SOVIET   = "L4_SOVIET_INVERSION"
    MARKOV   = "L5_MARKOV_PROGNOSIS"


class AnalyticsResult:
    """Об'єкт фінального аналітичного висновку системи для Блоку 5."""
    
    def __init__(self, query_id: str, raw_query: str):
        self.query_id = query_id
        self.raw_query = raw_query
        self.analyzed_at = time.time()
        self.layers_output: Dict[str, Any] = {}
        self.overall_confidence: float = 0.5
        self.bottlenecks: List[str] = []
        self.forecast_summary: str = ""
        self.advisory_notes: str = ""
        self.summary_metrics: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Конвертація аналітичної матриці в словник для репортера."""
        return {
            "query_id": self.query_id,
            "raw_query": self.raw_query,
            "analyzed_at": self.analyzed_at,
            "overall_confidence": self.overall_confidence,
            "bottlenecks": self.bottlenecks,
            "forecast_summary": self.forecast_summary,
            "advisory_notes": self.advisory_notes,
            "summary_metrics": self.summary_metrics,
            "layers_output": self.layers_output
        }


class Block4AnalyticsEngine:
    """
    Аналітичний двигун REILLY. 
    Розподіляє масиви збору за 4 сімействами та формує інтегральний висновок.
    """
    
    def __init__(self, router: Optional[ReillyLlmRouter] = None):
        self.router = router or ReillyLlmRouter()
        self.evaluator = MasterSignalEvaluator()
        
        # Ініціалізація 4 базових аналітичних цехів
        self.f_general = GeneralAnalyticsFamily()
        self.f_economic = EconomicAnalyticsFamily()
        self.f_scientific = ScientificAnalyticsFamily()
        self.f_social = SocialAnalyticsFamily()

    def analyze(self, inform_package: Any) -> AnalyticsResult:
        """Головний конвеєрний метод. Запускає комплексне міждисциплінарне моделювання."""
        logger.info("=" * 60)
        logger.info("[Analytics Core] 🧠 БЛОК 4 — ANALYTICS ENGINE | Глобальний запуск...")
        logger.info("=" * 60)

        pkg_data = inform_package.to_dict()
        result = AnalyticsResult(pkg_data["query_id"], pkg_data["raw_query"])

        # 1. Формуємо первинний пул живих сигналів з Блоку 2
        levels_data = pkg_data.get("levels_payload", {})
        raw_signals = []
        raw_signals.extend(levels_data.get("L3_OPEN", {}).get("semantic_data", []))
        raw_signals.extend(levels_data.get("L4_CLOSED", {}).get("hot_signals_data", []))

        # 2. Первинний прорахунок через Матрицю 5 Факторів
        direct_facts = 0
        inverted_mirrors = 0
        total_mass = 0.0

        for signal in raw_signals:
            passport = {
                "relevance": signal.get("relevance", 0.8),
                "days_ago": signal.get("days_ago", 0),
                "static_factor": signal.get("static_factor", 1.0),
                "importance": signal.get("importance", 0.5),
                "sentiment": signal.get("sentiment", 0.0),
                "source_positioning": signal.get("source_positioning", 0.0),
                "source_authority": signal.get("source_authority", 1.0)
            }
            evaluation = self.evaluator.evaluate_signal_passport(passport)
            if evaluation["final_weight"] > 0.0:
                total_mass += evaluation["final_weight"]
                if evaluation["vector"] == "DIRECT_FACT":
                    direct_facts += 1
                elif evaluation["vector"] == "INVERTED_MIRROR":
                    inverted_mirrors += 1

        # 3. КРОС-ЗАПУСК ВСІХ 4 СІМЕЙСТВ МЕТОДІВ (Наше оновлене серце)
        res_nato = self.f_general.analyze_nato_indicators(raw_signals)
        res_jervis = self.f_general.apply_jervis_discrimination(raw_signals)
        
        res_goldratt = self.f_economic.evaluate_goldratt_constraints(raw_signals)
        res_porter = self.f_economic.analyze_porter_value_chain(raw_signals)
        res_capital = self.f_economic.detect_capital_inversion_anomaly(raw_signals)
        
        res_markov = self.f_scientific.run_markov_prognosis(inverted_mirrors)
        res_zwicky = self.f_scientific.execute_zwicky_morphology(raw_signals)
        res_ishikawa = self.f_scientific.trace_chinese_ishikawa_root_cause(raw_signals)
        
        res_sna = self.f_social.run_social_network_analysis(raw_signals)
        res_stress = self.f_social.measure_linguistic_stress(raw_signals)
        res_stratagem = self.f_social.detect_chinese_stratagems(raw_signals)

        # 4. Зшиваємо результати у твої класичні 5 концептуальних шарів звітности
        result.bottlenecks = res_goldratt["all_detected_bottlenecks"]
        result.forecast_summary = res_markov["most_probable_state_6_months"]
        
        # Шар L1
        result.layers_output[AnalysisLayer.GREENE.value] = {
            "primary_driver": "Максимізація темпів завантаження ВПК",
            "ishikawa_root_cause": res_ishikawa["ishikawa_determined_root_cause"],
            "accumulated_mass": round(total_mass, 2)
        }
        # Шар L2
        result.layers_output[AnalysisLayer.JERVIS.value] = {
            "signal_to_noise_ratio": res_jervis["signal_to_noise_ratio"],
            "information_density_pct": res_jervis["information_density_pct"],
            "nato_alert_level": res_nato["nato_alert_level"]
        }
        # Шар L3
        result.layers_output[AnalysisLayer.GOLDRATT.value] = {
            "critical_constraint": res_goldratt["critical_system_constraint"],
            "system_capacity_utilization_pct": res_goldratt["system_capacity_utilization_pct"],
            "value_chain": res_porter["value_chain_matrix"]
        }
        # Шар L4
        result.layers_output[AnalysisLayer.SOVIET.value] = {
            "capital_inversion_found": res_capital["capital_inversion_anomaly_found"],
            "capital_verdict": res_capital["verdict"],
            "detected_chinese_stratagem": res_stratagem["detected_chinese_stratagem_code"],
            "inversion_markers_found": inverted_mirrors
        }
        # Шар L5
        result.layers_output[AnalysisLayer.MARKOV.value] = {
            "forecast_6_months": res_markov["most_probable_state_6_months"],
            "crisis_probability": res_markov["crisis_probability"],
            "morphological_space_code": res_zwicky["morphological_space_combination_code"],
            "network_topology": res_sna["network_topology_type"],
            "population_stress_index": res_stress["population_stress_index"]
        }

        # Формуємо підсумкові метрики
        total_processed = len(raw_signals)
        avg_mass = (total_mass / total_processed) if total_processed > 0 else 0.0
        
        result.summary_metrics = {
            "total_signals_verified": total_processed,
            "direct_facts_detected": direct_facts,
            "manipulations_inverted": inverted_mirrors,
            "average_signal_mass": round(avg_mass, 3),
            "intelligence_integrity_index": "SECURE" if inverted_mirrors < 2 else "HEAVY_PROPAGANDA"
        }

        # Розрахунок глобального коефіцієнта впевненості
        base_conf = 0.85 if res_stress["population_stress_index"] < 0.5 else 0.65
        result.overall_confidence = round(base_conf * 0.95, 3)
        
        result.forecast_summary = (
            f"З ймовірністю {int(res_markov['crisis_probability'] * 100)}% система увійде у фазу "
            f"кризи за кодом {res_zwicky['morphological_space_combination_code']}."
        )
        result.advisory_notes = (
            f"Критичні обмеження: {', '.join(result.bottlenecks) if result.bottlenecks else 'NONE'}. "
            f"Виявлено китайську стратагему: {res_stratagem['detected_chinese_stratagem_code']}."
        )

        logger.info("[Analytics Core] ✅ Розрахунок завершено. Впевненість системи: %.2f", 
                    result.overall_confidence)
        logger.info("=" * 60)

        return result