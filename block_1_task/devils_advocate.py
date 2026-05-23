#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 1 — DEVILS ADVOCATE (Контур внутрішньої рефлексії)
Етап 1.5: Стрес-тест програми дій на логічні прогалини та упередженість збору.
Path: /home/ubuntu/IT-PROJECTS/REILLY/block_1_task/devils_advocate.py
"""

import logging
from typing import List, Dict, Any
from core_intelligence.router import ReillyLlmRouter
from .models import ActionProgram

logger = logging.getLogger(__name__)

class DevilsAdvocate:
    """
    Компонент внутрішнього опонента. Працює як аналітичний фільтр, 
    який захищає систему від ШІ-галюцинацій та поверхневого планування.
    """
    def __init__(self, router: ReillyLlmRouter):
        self.router = router

    def audit_plan(self, query: str, action_program: ActionProgram) -> List[Dict[str, str]]:
        """
        Проводить всебічний аудит сформованої програми дій.
        Повертає список знайдених уразливостей (vulnerabilities).
        """
        logger.info("[Опонент] 🛡️ Запуск криміналістичного аналізу програми дій...")
        vulnerabilities = []
        
        tasks = action_program.search_tasks
        
        # 1. МАТЕМАТИЧНИЙ АНАЛІЗ СТРУКТУРИ ТАСОК (Локальні правила)
        has_semantic = any(t.search_type == "SEMANTIC" for t in tasks)
        has_spatial = any(t.search_type == "SPATIAL_INFRA" for t in tasks)
        has_anomalies = any(t.search_type in ["TEMPORAL_ANOMALY", "LINGUISTIC_STRESS"] for t in tasks)
        
        # Перевірка 1.1: Ризик Confirmation Bias (Упередженість підтвердження)
        # Якщо є штурм HTML, але немає семантичного контуру для порівняння смислів
        if has_spatial and not has_semantic:
            logger.warning("[Опонент] ⚠️ Виявлено BIAS_RISK: План ігнорує семантичний баланс.")
            vulnerabilities.append({
                "type": "BIAS_RISK",
                "severity": "HIGH",
                "description": "План фокусується на сирої інфраструктурі, але не закладає семантичний збір фонового контексту."
            })

        # Перевірка 1.2: Перевантаження пошуковим шумом
        # Якщо система нагенерувала забагато базових SERP запитів, ми потонемо в репостах новин
        serp_count = sum(1 for t in tasks if t.bright_data_tool == "SERP_API")
        if serp_count > 4:
            logger.warning("[Опонент] ⚠️ Виявлено OVER-RELIANCE: Надлишок пошукового шуму.")
            vulnerabilities.append({
                "type": "OVER-RELIANCE_ON_SEARCH",
                "severity": "MEDIUM",
                "description": f"Занадто багато розмитих запитів до пошукових систем ({serp_count}). Високий ризик збору медійного спаму."
            })

        # 2. КОРЕЛЯЦІЯ ЧЕРЕЗ ШІ-РОУТЕР (Пошук прихованих смислових прогалин)
        # Просимо ШІ виступити в ролі жорсткого військового аналітика-критика
        try:
            logger.info("[Опонент] Запит до ШІ-роутера для пошуку прихованих аналітичних прогалин плану...")
            
            # Формуємо список поточних тасок у вигляді короткого тексту для ШІ
            tasks_summary = []
            for t in tasks:
                tasks_summary.append(f"- [{t.search_type}] за допомогою {t.bright_data_tool}: {t.meta_instruction}")
            tasks_block = "\n".join(tasks_summary)

            critic_prompt = (
                f"Ти — досвідчений аналітик розвідки Сідней Рейлі. Перед тобою план збору даних.\n"
                f"Початкова аналітична ціль: {query}\n"
                f"Поточний сформований план завдань:\n{tasks_block}\n\n"
                f"Знайди головну критичну прогалину у цьому плані. Чого не вистачає? Що пропущено?\n"
                f"Якщо все ідеально, напиши: APPROVED.\n"
                f"Якщо знайдено дірку, почни відповідь строго з коду: CRITICAL_GAP: <опис прогалини>"
            )

            ai_criticism = self.router.execute_critic(critic_prompt)
            
            if ai_criticism and "CRITICAL_GAP" in ai_criticism:
                gap_description = ai_criticism.replace("CRITICAL_GAP:", "").strip()
                logger.warning("[Опонент] ⚠️ ШІ виявив критичну аналітичну прогалину: %s", gap_description)
                vulnerabilities.append({
                    "type": "AI_CRITICAL_GAP",
                    "severity": "HIGH",
                    "description": gap_description
                })
            else:
                logger.info("[Опонент] ШІ-контур підтвердив стійкість логіки плану.")

        except Exception as e:
            logger.error("[Опонент] Помилка ШІ-контуру критики: %s. Використовуємо лише локальні правила.", str(e))

        logger.info("[Опонент] 🔍 Аудит завершено. Знайдено уразливостей: %d", len(vulnerabilities))
        return vulnerabilities