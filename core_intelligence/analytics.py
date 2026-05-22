#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 4 — Dual-Contour No-Zero Truth Evaluation
Target Directory: /home/ubuntu/IT-PROJECTS/00.Wibe-coding_projects/Wibe_Commander/
Line Length Limit: 100 characters
"""

import logging

logger = logging.getLogger(__name__)


def calculate_dual_contour_weight(value_index: float, truth_index: float) -> dict:
    """
    Розрахунок ваги сигналу за двоконтурною шкалою без нуля.
    Діапазони: [+1.0 ... +2.0] (Пряма правда) та [-1.0 ... -2.0] (Інверсія).
    """
    # Валідація загороджувального контуру на випадок помилки передачі нуля
    if truth_index == 0.0:
        logger.warning("Zero detected in truth_index. Forced fallback to baseline +1.0")
        truth_index = 1.0

    # Визначення абсолютної сили модифікатора (масштаб від 1.0 до 2.0)
    multiplier = abs(truth_index)
    
    # Розрахунок підсумкової аналітичної ваги об'єкта
    final_weight = value_index * multiplier

    # Розподіл потоків обробки за полярністю знака
    if truth_index < 0:
        return {
            "final_weight": final_weight,
            "semantic_vector": "INVERTED_MIRROR",
            "log_note": "Systematic distortion detected. Read message content in reverse."
        }
        
    return {
        "final_weight": final_weight,
        "semantic_vector": "DIRECT_FACT",
        "log_note": "Legitimate signal. Process data as a direct fact."
    }


# --- Тест-драйв нового математичного двигуна ---
if __name__ == "__main__":
    # Тест 1: Важка державна дезінформація (-2.0) по критичному об'єкту (0.8)
    propaganda_signal = calculate_dual_contour_weight(value_index=0.8, truth_index=-2.0)
    print(f"Пропаганда (-2.0): {propaganda_signal}\n")

    # Тест 2: Рядова неперевірена інформація (+1.0) з високою цінністю (0.7)
    rumor_signal = calculate_dual_contour_weight(value_index=0.7, truth_index=1.0)
    print(f"Базова чутка (+1.0): {rumor_signal}")