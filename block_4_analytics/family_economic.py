#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 4 — FAMILY ECONOMIC (Економічні та інфраструктурні методи)
Path: block_4_analytics/family_economic.py
Line Length Limit: 100 characters

Contains Goldratt Bottleneck assessment, Porter Value Chain steps, and Capital Inversion.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class EconomicAnalyticsFamily:
    """Сімейство економічних та інфраструктурних методів аналізу складної промисловості."""

    def __init__(self):
        logger.info("[Family Economic] 🏭 Активовано контур економічного та логістичного аналізу.")

    def evaluate_goldratt_constraints(self, raw_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Теорія обмежень (Е. Ґолдратт). Шукає маркери дефіциту ресурсів, 
        кадрового голоду та перевантаження ліній залізниці / енергомереж.
        """
        detected_bottlenecks = []
        full_text = " ".join([f"{s.get('title', '')} {s.get('text_snippet', '')}".lower() for s in raw_signals])

        # Сигнатурні маркери звуження пропускної здатності
        if any(w in full_text for w in ["дефіцит кадри", "вакансі", "шукає інженер"]):
            detected_bottlenecks.append("HUMAN_RESOURCE_CONSTRAINT (Кадровий дефіцит інженерів)")
        if any(w in full_text for w in ["затримка", "вагон", "затор", "колій"]):
            detected_bottlenecks.append("LOGISTIC_TRANSPORT_CONSTRAINT (Транспортний затор інфраструктури)")
        if any(w in full_text for w in ["ліміт електро", "дефіцит метал", "сировин"]):
            detected_bottlenecks.append("RAW_MATERIAL_ENERGY_CONSTRAINT (Обмеження сировини/енергії)")

        capacity_utilization = 50.0 + (len(detected_bottlenecks) * 15.0)
        capacity_utilization = min(98.5, capacity_utilization)

        return {
            "critical_system_constraint": detected_bottlenecks[0] if detected_bottlenecks else "NONE",
            "system_capacity_utilization_pct": round(capacity_utilization, 1),
            "all_detected_bottlenecks": detected_bottlenecks
        }

    def analyze_porter_value_chain(self, raw_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Аналіз ланцюжка доданої вартості Майкла Портера.
        Сканує три основні зони об'єкта: Inbound (Сировина), Operations (Цехи), Outbound (Логістика).
        """
        full_text = " ".join([f"{s.get('title', '')} {s.get('text_snippet', '')}".lower() for s in raw_signals])
        
        chain_status = {
            "inbound_logistics_raw": "STABLE" if "постачан" in full_text else "UNKNOWN_RISK",
            "operations_manufacturing": "STABLE" if "цех" in full_text or "завод" in full_text else "UNKNOWN_RISK",
            "outbound_logistics_delivery": "STABLE" if "відвантаж" in full_text or "маршрут" in full_text else "UNKNOWN_RISK"
        }
        
        return {"value_chain_matrix": chain_status}

    def detect_capital_inversion_anomaly(self, raw_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Патерн інверсії капіталу (Радянсько-Китайський аналіз).
        Фіксує аномалію, якщо фінансові витрати (тендери) зростають,
        але фізичні ознаки активності (рух вагонів, відвантаження) падають або стагнують.
        """
        full_text = " ".join([f"{s.get('title', '')} {s.get('text_snippet', '')}".lower() for s in raw_signals])
        
        # Фіксуємо фінансовий слід
        has_high_finance = any(w in full_text for w in ["тендер", "закупівл", "мільйон", "мільярд"])
        # Фіксуємо фізичний слід
        has_low_physics = any(w in full_text for w in ["затримка", "стагнація", "зрив постачан", "дефіцит"])

        inversion_anomaly_detected = False
        risk_score = 0.1

        if has_high_finance and has_low_physics:
            inversion_anomaly_detected = True
            risk_score = 0.85
        elif has_high_finance:
            risk_score = 0.35

        return {
            "capital_inversion_anomaly_found": inversion_anomaly_detected,
            "financial_vs_physical_risk_score": risk_score,
            "verdict": "HEAVY_STRUCTURAL_CORRUPTION_OR_BUBBLE" if inversion_anomaly_detected else "NORMAL"
        }


# --- Локальний тест модуля ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = EconomicAnalyticsFamily()
    
    mock_economic_data = [
        {"title": "Тендери на мільярди рублів", "text_snippet": "Закупівля металу розширюється щодня"},
        {"title": "Критична затримка вагонів на вузлах", "text_snippet": "Шукають інженерів через кадровий дефіцит"}
    ]
    
    goldratt = engine.evaluate_goldratt_constraints(mock_economic_data)
    porter = engine.analyze_porter_value_chain(mock_economic_data)
    capital = engine.detect_capital_inversion_anomaly(mock_economic_data)
    
    print("\n--- РЕЗУЛЬТАТИ ТЕСТУ БЛОКУ ЕКОНОМІКИ ---")
    print(f"Вузькі місця (Ґолдратт): {goldratt['all_detected_bottlenecks']}")
    print(f"Завантаження системи: {goldratt['system_capacity_utilization_pct']}%")
    print(f"Ланцюжок Портера: {porter['value_chain_matrix']}")
    print(f"Аномалія інверсії капіталу: {capital['capital_inversion_anomaly_found']} (Вердикт: {capital['verdict']})")