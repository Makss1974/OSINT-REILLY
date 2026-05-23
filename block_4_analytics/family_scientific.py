#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 4 — FAMILY SCIENTIFIC (Наукові та системні методи аналізу)
Path: block_4_analytics/family_scientific.py
Line Length Limit: 100 characters

Contains Markov Chains prediction, Zwicky Morphological analysis, and Chinese Ishikawa tracking.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ScientificAnalyticsFamily:
    """Сімейство наукових, системних та ймовірнісних методів стратегічного прогнозування."""

    def __init__(self):
        logger.info("[Family Scientific] 🔬 Активовано контур наукового та системного моделювання.")

    def run_markov_prognosis(self, inverted_markers_count: int) -> Dict[str, Any]:
        """
        Марковські ланцюги. Розраховує матрицю переходів станів та визначає
        найбільш ймовірний стан системи (STABLE, STRESSED, CRISIS) через 6 місяців.
        """
        # Динамічно коригуємо ймовірність кризи на основі виявлених Блоком 4 викривлень
        prob_crisis_shift = min(0.40, inverted_markers_count * 0.10)
        
        states = ["STABLE", "STRESSED", "CRISIS"]
        # Базова матриця переходів: [P(S->S), P(S->Str), P(S->C)]
        transition_matrix = [
            [round(0.3 - (prob_crisis_shift * 0.5), 2), round(0.5, 2), round(0.2 + prob_crisis_shift, 2)],
            [0.0, 0.3, 0.7],
            [0.0, 0.0, 1.0]
        ]
        
        # Визначаємо фінальний прогнозний вектор
        prob_crisis = transition_matrix[0][2]
        if prob_crisis > 0.45:
            most_probable = "CRISIS"
        elif transition_matrix[0][1] > transition_matrix[0][0]:
            most_probable = "STRESSED"
        else:
            most_probable = "STABLE"

        return {
            "system_states": states,
            "calculated_transition_matrix": transition_matrix,
            "most_probable_state_6_months": most_probable,
            "crisis_probability": prob_crisis
        }

    def execute_zwicky_morphology(self, raw_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Морфологічний аналіз Фріца Цвіккі. Розкладає систему на параметри
        та вираховує унікальний індекс комбінації для виявлення прихованих сценаріїв.
        """
        full_text = " ".join([f"{s.get('title', '')} {s.get('text_snippet', '')}".lower() for s in raw_signals])
        
        # Морфологічна вісь 1: Сировина
        axis_raw = "ALTERNATIVE_SUPPLY" if "китай" in full_text or "імпорт" in full_text else "LOCAL_SUPPLY"
        # Морфологічна вісь 2: Кадри
        axis_human = "CRITICAL_DEFICIT" if "вакансі" in full_text or "дефіцит" in full_text else "NORMAL_CAPACITY"
        
        morphological_space_code = f"RAW_{axis_raw} // HUM_{axis_human}"
        
        return {
            "morphological_space_combination_code": morphological_space_code,
            "unanticipated_black_swan_risk": "HIGH" if "deficit" in morphological_space_code.lower() else "LOW"
        }

    def trace_chinese_ishikawa_root_cause(self, raw_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Причинно-наслідковий метод КНР (Модифікована "Річка ефектів" Ісікави).
        Розкручує ланцюжок від наслідку (аномалії) до першопричини (Root Cause).
        """
        full_text = " ".join([f"{s.get('title', '')} {s.get('text_snippet', '')}".lower() for s in raw_signals])
        
        root_cause = "EXTERNAL_MACRO_FACTORS"
        if "вакансі" in full_text or "інженер" in full_text:
            root_cause = "INTERNAL_STRUCTURAL_LABOR_COLLAPSE (Внутрішній системний крах кадрів)"
        elif "затримка" in full_text or "вагон" in full_text:
            root_cause = "LOGISTIC_INFRASTRUCTURE_DEGRADATION (Знос транспортних фондів)"

        return {
            "ishikawa_determined_root_cause": root_cause,
            "system_integrity_score": 0.4 if "collapse" in root_cause.lower() else 0.8
        }


# --- Локальний тест модуля ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = ScientificAnalyticsFamily()
    
    mock_scientific_data = [
        {"title": "Імпорт обладнання з Китаю", "text_snippet": "Зафіксовано нові вакансії на підприємстві"}
    ]
    
    # Симулюємо, що раніше було виявлено 3 дзеркальні аномалії
    markov = engine.run_markov_prognosis(inverted_markers_count=3)
    zwicky = engine.execute_zwicky_morphology(mock_scientific_data)
    ishikawa = engine.trace_chinese_ishikawa_root_cause(mock_scientific_data)
    
    print("\n--- РЕЗУЛЬТАТИ ТЕСТУ НАУКОВОГО БЛОКУ ---")
    print(f"Марковський стан через 6 міс: {markov['most_probable_state_6_months']} (Ймовірність кризи: {markov['crisis_probability']})")
    print(f"Матриця Маркова: {markov['calculated_transition_matrix'][0]}")
    print(f"Код простору Цвіккі: {zwicky['morphological_space_combination_code']}")
    print(f"Першопричина за Ісікавою (КНР): {ishikawa['ishikawa_determined_root_cause']}")