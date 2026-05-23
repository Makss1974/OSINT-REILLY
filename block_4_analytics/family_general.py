#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 4 — FAMILY GENERAL (Загальні аналітичні методи)
Path: block_4_analytics/family_general.py
Line Length Limit: 100 characters

Contains the NATO Indicators & Warning Framework and Jervis Signal Discrimination.
"""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class GeneralAnalyticsFamily:
    """Сімейство загальних, семантичних та статистичних методів аналізу (Матриця НАТО)."""

    # Динамічна матриця індикаторів розвідки НАТО (Indicators & Warning Framework)
    NATO_INDICATORS = {
        "IND_MIL_01": {"weight": 0.45, "keywords": [r"вакансі", r"цех", r"робоч.*руки", r"майстер"]},
        "IND_MIL_02": {"weight": 0.40, "keywords": [r"залізнич", r"маршрут", r"вагон", r"платформ"]},
        "IND_ECO_01": {"weight": 0.35, "keywords": [r"тендер", r"закупівл", r"прокат", r"метал"]},
        "IND_ECO_02": {"weight": 0.30, "keywords": [r"трансформатор", r"електро", r"ліміт", r"квт"]},
        "IND_SOC_01": {"weight": 0.25, "keywords": [r"протест", r"затримка.*зарплат", r"скарг"]}
    }

    def __init__(self):
        logger.info("[Family General] 📊 Активовано контур загальних методів та матрицю НАТО.")

    def analyze_nato_indicators(self, raw_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Проганяє текстовий масив через сито непрямих ознак розвідки НАТО.
        Рахує сумарну аналітичну масу активованих індикаторів.
        """
        activated_indicators = set()
        total_activated_weight = 0.0
        evidence_snippets = []

        # Об'єднуємо всі текстові зрізи в єдиний лінгвістичний масив для сканування
        full_text_pool = " ".join([
            f"{s.get('title', '')} {s.get('text_snippet', '')}".lower() 
            for s in raw_signals
        ])

        # Шукаємо збіги за сигнатурами регулярних виразів
        for ind_id, meta in self.NATO_INDICATORS.items():
            for regex in meta["keywords"]:
                if re.search(regex, full_text_pool):
                    if ind_id not in activated_indicators:
                        activated_indicators.add(ind_id)
                        total_activated_weight += meta["weight"]
                        logger.info(f"[NATO Matrix] Triggered: {ind_id} (Weight: {meta['weight']})")

        # Визначаємо рівень загрози / активності процесу на основі порогів НАТО
        if total_activated_weight >= 0.75:
            alert_level = "CRITICAL_ALERT_CONFIRMED"
        elif total_activated_weight >= 0.40:
            alert_level = "WARNING_ACTIVITY_DETECTED"
        else:
            alert_level = "STABLE_BACKGROUND_NOISE"

        return {
            "nato_alert_level": alert_level,
            "accumulated_indicator_mass": round(total_activated_weight, 2),
            "activated_indicators_list": list(activated_indicators)
        }

    @staticmethod
    def apply_jervis_discrimination(raw_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Метод Роберта Джервіса: Дискримінація корисного сигналу від шуму.
        Рахує відношення чистих фактів до загального спаму/порожніх лінків.
        """
        total_input = len(raw_signals)
        useful_signals = 0
        noise_signals = 0

        for s in raw_signals:
            # Якщо сигнал має мінімальну вагу або міститьsnippet, вважаємо його корисним
            if len(s.get("text_snippet", "").strip()) > 30:
                useful_signals += 1
            else:
                noise_signals += 1

        snr = round(useful_signals / max(1, noise_signals), 2)
        
        return {
            "total_signals_examined": total_input,
            "signal_to_noise_ratio": snr,
            "information_density_pct": round((useful_signals / max(1, total_input)) * 100, 1)
        }


# --- Локальний тест модуля ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = GeneralAnalyticsFamily()
    
    # Симулюємо дані, накрадені ботами Блоку №2
    mock_data = [
        {"title": "Завод оголосив тендер на закупівлю металу", "text_snippet": "Потрібні нові майстри в цех №3"},
        {"title": "Графік руху залізничних вагонів", "text_snippet": "Платформи з прокатом затримано на станції"}
    ]
    
    nato_res = engine.analyze_nato_indicators(mock_data)
    jervis_res = engine.apply_jervis_discrimination(mock_data)
    
    print("\n--- РЕЗУЛЬТАТИ ТЕСТУ МАТРИЦІ НАТО ---")
    print(f"Статус: {nato_res['nato_alert_level']}")
    print(f"Сумарна вага: {nato_res['accumulated_indicator_mass']}")
    print(f"Активовані ID: {nato_res['activated_indicators_list']}")
    print(f"Щільність сигналу (Джервіс): {jervis_res['information_density_pct']}%")