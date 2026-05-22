#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 4 — Master Signal Evaluation Matrix
Path: core_intelligence/analytics/signal_evaluator.py
Line Length Limit: 100 characters

Implementation of Max's 5-Factor Signal Passport Matrix.
Translates qualitative intelligence markers into mathematical mass and directional vectors.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MasterSignalEvaluator:
    """Уніфікований оцінювач сигналів за 5-факторною матрицею розвідки."""

    @staticmethod
    def evaluate_signal_passport(report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Зводить 5 факторів розвідки в єдину математичну модель оцінки сигналу.
        Приймає паспорт сигналу, повертає фінальну вагу та вектор обробки.
        """
        try:
            # 1. Фільтр релевантності (Загороджувальний затвор)
            relevance = float(report.get("relevance", 0.0))
            if relevance < 0.4:
                return {
                    "final_weight": 0.0,
                    "vector": "DROPPED",
                    "status": "DROPPED_NOT_RELEVANT"
                }

            # 2. Розрахунок актуальності з урахуванням статичності (Ентропія часу)
            days = max(0.0, float(report.get("days_ago", 0.0)))
            static_factor = max(0.0, min(1.0, float(report.get("static_factor", 1.0))))
            
            # Формула згасання: Актуальність = 1 / (1 + (Днів * S))
            actual_multiplier = 1.0 / (1.0 + (days * static_factor))

            # 3. Базова важливість та сентимент контенту
            importance = max(0.1, min(1.0, float(report.get("importance", 0.1))))
            sentiment = max(-1.0, min(1.0, float(report.get("sentiment", 0.0))))

            # 4 & 5. Оцінка індексу істинності через Позиціонування та Авторитет джерела
            source_bias = max(-1.0, min(1.0, float(report.get("source_positioning", 0.0))))
            source_authority = max(1.0, min(2.0, float(report.get("source_authority", 1.0))))

            # Математичний синтез істинності (Двоконтурна модель без нуля)
            # Якщо зацікавлене джерело занадто хвалить/бреше — вмикаємо інверсію
            if source_bias * sentiment > 0.7:
                # Сигнал системно викривлений. Перехід у негативний дзеркальний контур
                truth_index = -1.5 * source_authority
            else:
                # Сигнал вважається прямим фактом (або нейтральним вкидом)
                truth_index = 1.0 * source_authority

            # Фінальний розрахунок аналітичної маси сигналу
            final_weight = actual_multiplier * importance * abs(truth_index)

            return {
                "final_weight": round(final_weight, 3),
                "vector": "DIRECT_FACT" if truth_index > 0 else "INVERTED_MIRROR",
                "status": "PROCESSED_SUCCESSFULLY"
            }

        except (ValueError, TypeError) as e:
            logger.error(f"Malformed signal data passport packet: {e}")
            return {
                "final_weight": 0.0,
                "vector": "ERROR",
                "status": "FAILED_MALFORMED_DATA"
            }


# ─────────────────────────────────────────────────────────────────────────────
# Комплексний Тест-драйв Матриці (Ручний запуск: python signal_evaluator.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    evaluator = MasterSignalEvaluator()

    print("=" * 70)
    print("RUNNING REILLY MASTER SIGNAL EVALUATOR TANK TEST")
    print("=" * 70)

    # Кейс 1: Абсолютна статика (Іван помер / Подія 2-річної давнини, важлива)
    case_static = {
        "relevance": 1.0,
        "days_ago": 730,          # 2 роки тому
        "static_factor": 0.0,      # Абсолютна статика (S = 0)
        "importance": 0.9,
        "sentiment": 0.0,          # Сухий факт
        "source_positioning": 0.0, # Нейтральний реєстр
        "source_authority": 2.0    # Максимальний авторитет держави
    }
    res_1 = evaluator.evaluate_signal_passport(case_static)
    print(f"Кейс 1 (Статичний факт): {res_1}")

    # Кейс 2: Пропаганда (Заява зацікавленої фірми / Твоя чернетка)
    case_propaganda = {
        "relevance": 0.9,
        "days_ago": 5,
        "static_factor": 1.0,      # Динамічний ринок
        "importance": 0.8,
        "sentiment": 0.9,          # Тотальний позитив
        "source_positioning": 0.9, # Прямий фінансовий інтерес авторів
        "source_authority": 1.2    # Комерсанти
    }
    res_2 = evaluator.evaluate_signal_passport(case_propaganda)
    print(f"Кейс 2 (Аномальний позитив): {res_2}")

    # Кейс 3: Застаріла гаряча новина (Курс долара 10 днів тому)
    case_stale = {
        "relevance": 0.9,
        "days_ago": 10,
        "static_factor": 1.0,      # Радикальна динаміка (S = 1)
        "importance": 0.5,
        "sentiment": 0.1,
        "source_positioning": 0.0,
        "source_authority": 1.0
    }
    res_3 = evaluator.evaluate_signal_passport(case_stale)
    print(f"Кейс 3 (Застаріла новина): {res_3}")
    print("=" * 70)