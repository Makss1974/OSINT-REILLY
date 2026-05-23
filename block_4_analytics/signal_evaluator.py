#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 4 — Master Signal Evaluation Matrix
Path: block_4_analytics/signal_evaluator.py
Line Length Limit: 100 characters

Implementation of Max's 5-Factor Signal Passport Matrix.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MasterSignalEvaluator:
    """Оцінювач сигналів за 5-факторною матрицею розвідки (Admiralty Code)."""

    @staticmethod
    def evaluate_signal_passport(report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Зводить 5 факторів Макса в єдину математичну модель оцінки сигналу.
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
            
            # Твоя формула згасання: 1 / (1 + (Днів * S))
            actual_multiplier = 1.0 / (1.0 + (days * static_factor))

            # 3. Базова важливість та сентимент контенту
            importance = max(0.1, min(1.0, float(report.get("importance", 0.1))))
            sentiment = max(-1.0, min(1.0, float(report.get("sentiment", 0.0))))

            # 4 & 5. Оцінка істинності через Позиціонування та Авторитет джерела
            source_bias = max(-1.0, min(1.0, float(report.get("source_positioning", 0.0))))
            source_authority = max(1.0, min(2.0, float(report.get("source_authority", 1.0))))

            # Математичний синтез істинності (Двоконтурна модель)
            # Якщо зацікавлене джерело занадто хвалить — вмикаємо інверсію
            if source_bias * sentiment > 0.7:
                truth_index = -1.5 * source_authority  # Вектор дзеркала
            else:
                truth_index = 1.0 * source_authority   # Прямий факт

            # Фінальний розрахунок аналітичної маси сигналу
            final_weight = actual_multiplier * importance * abs(truth_index)

            return {
                "final_weight": round(final_weight, 3),
                "vector": "DIRECT_FACT" if truth_index > 0 else "INVERTED_MIRROR",
                "status": "PROCESSED_SUCCESSFULLY"
            }

        except (ValueError, TypeError) as e:
            logger.error(f"Malformed signal packet: {e}")
            return {
                "final_weight": 0.0,
                "vector": "ERROR",
                "status": "FAILED_MALFORMED_DATA"
            }