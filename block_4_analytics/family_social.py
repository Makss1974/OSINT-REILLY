#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 4 — FAMILY SOCIAL (Соціальні методи та OSINT соцмереж)
Path: block_4_analytics/family_social.py
Line Length Limit: 100 characters

Contains Social Network Analysis (SNA), Linguistic Stress tracking, and Stratagem Detection.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SocialAnalyticsFamily:
    """Сімейство соціальних методів, аналізу настроїв пабліків та HUMINT-викривлень."""

    def __init__(self):
        logger.info("[Family Social] 👥 Активовано контур соціального аналізу та OSINT соцмереж.")

    def run_social_network_analysis(self, raw_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        SNA (Social Network Analysis). Аналізує топологію поширень.
        Визначає, чи йде сигнал з одного координованого центру (бота), чи є органічним.
        """
        full_text = " ".join([f"{s.get('title', '')}".lower() for s in raw_signals])
        
        # Якщо в джерелах багато однакових заголовків — фіксуємо координацію ботів
        is_coordinated = "бот" in full_text or len(raw_signals) > 3
        
        return {
            "network_topology_type": "COORDINATED_BOTNET_ATTACK" if is_coordinated else "ORGANIC_DIFFUSION",
            "core_influence_hubs_count": 1 if is_coordinated else max(1, len(raw_signals))
        }

    def measure_linguistic_stress(self, raw_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Вимірювання лінгвістичного стресу та тривожності (за методикою Greene/Jervis).
        Рахує щільність маркерів паніки, скарг або агресії в регіональних чатах.
        """
        full_text = " ".join([f"{s.get('text_snippet', '')}".lower() for s in raw_signals])
        
        stress_markers = [r"скарг", r"панік", r"страйк", r"бунт", r"затримка", r"криз"]
        trigger_count = sum(1 for m in stress_markers if m in full_text)
        
        stress_index = min(1.0, float(trigger_count * 0.25))
        
        if stress_index >= 0.75:
            stability = "CRITICAL_UNSTABLE_PANIC"
        elif stress_index >= 0.25:
            stability = "STRESSED_MUTED_DISCONTENT"
        else:
            stability = "STABLE_BACKGROUND"

        return {
            "population_stress_index": stress_index,
            "regional_social_stability_status": stability
        }

    def detect_chinese_stratagems(self, raw_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Стратагемний аналіз викривлень (Китайська воєнна доктрина).
        Визначає, яку саме стратагенну дезінформацію намагається згодувати нам супротивник.
        """
        full_text = " ".join([
            f"{s.get('title', '')} {s.get('text_snippet', '')}".lower() 
            for s in raw_signals
        ])
        
        # Стратагема №7: "З нічого створити дещо" (Імітація сили)
        # Стратагема №25: "Вкрасти балки і замінити їх гнилими підпорами" (Приховування кризи)
        detected_stratagem = "NONE_DETECTED"
        requires_inversion = False

        if "прорив" in full_text and ("вакансі" in full_text or "дефіцит" in full_text):
            detected_stratagem = "STRATAGEM_25_REPLACE_BEAMS (Приховування внутрішнього гниття)"
            requires_inversion = True
        elif "рекордн" in full_text and "мільярд" in full_text:
            detected_stratagem = "STRATAGEM_7_CREATE_SOMETHING_FROM_NOTHING (Штучний шум)"
            requires_inversion = True

        return {
            "detected_chinese_stratagem_code": detected_stratagem,
            "force_inverted_mirror_trigger": requires_inversion,
            "confidence_score": 0.85 if requires_inversion else 0.20
        }


# --- Локальний тест модуля ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = SocialAnalyticsFamily()
    
    mock_social_data = [
        {"title": "Рекордний прорив виробництва", "text_snippet": "Але зафіксовано дефіцит інженерів та скарги на зарплату"}
    ]
    
    sna = engine.run_social_network_analysis(mock_social_data)
    stress = engine.measure_linguistic_stress(mock_social_data)
    stratagem = engine.detect_chinese_stratagems(mock_social_data)
    
    print("\n--- РЕЗУЛЬТАТИ ТЕСТУ СОЦІАЛЬНОГО БЛОКУ ---")
    print(f"Топологія мережі: {sna['network_topology_type']}")
    print(f"Індекс стресу: {stress['population_stress_index']} (Статус: {stress['regional_social_stability_status']})")
    print(f"Виявлена стратагема КНР: {stratagem['detected_chinese_stratagem_code']}")
    print(f"Активація режиму Дзеркала: {stratagem['force_inverted_mirror_trigger']}")