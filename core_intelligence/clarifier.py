#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY: Block #1 - Clarification & Context Extraction Agent
Path: /home/ubuntu/IT-PROJECTS/00.Wibe-coding_projects/Wibe_Commander/core_intelligence/clarifier.py
Line Length Limit: 100 characters
"""

import json

class ReillyClarifierAgent:
    def __init__(self):
        # Суворий системний паттерн поведінки для ШІ
        self.system_instruction = (
            "You are REILLY-Architect. Your goal is to refine raw OSINT queries.\n"
            "Never agree to generic search. You must extract exactly 4 variables:\n"
            "1. Target_Geo (Where?)\n"
            "2. Target_Object (What factory/industry?)\n"
            "3. Time_Frame (Past month? 2026 context?)\n"
            "4. Analytical_Focus (Which of the 6 domains?)\n"
            "Be concise, professional, and slightly paranoid. Do not use fluff."
        )

    def generate_clarification_question(self, user_query: str, chat_history: list = None) -> str:
        """
        Аналізує поточний стан діалогу та формує чітке запитання, 
        якщо якихось параметрів не вистачає.
        """
        # Тут буде виклик LLM API (наприклад, Gemini Client), куди ми передаємо:
        # self.system_instruction + user_query + chat_history
        
        # Емуляція логіки ШІ на випадок відсутності конкретики:
        if "саратов" in user_query.lower() and "завод" in user_query.lower():
            return (
                "🤖 REILLY-Architect: Об'єкт (Завод у Саратові) зафіксовано. "
                "Які саме матеріальні сліди шукаємо: кадрові зміни (вакансії ВПК), "
                "залізничну логістику чи фінансові реєстри? Вкажіть часовий проміжок."
            )
        return "🤖 REILLY-Architect: Вкажіть конкретний об'єкт та географію для аналізу."

    def finalize_task_json(self, conversation_result: str) -> dict:
        """
        Коли діалог завершено, цей метод переводить текст у сухі числові 
        та словесні параметри для Блоку №2 (Збір).
        """
        # Цей JSON буде згенеровано моделлю на виході
        structured_parameters = {
            "execution_allowed": True,
            "extracted_variables": {
                "target_geo": "Saratov_Region",
                "target_object": "Aviation_Plant_No3",
                "time_frame": "Last_30_days",
                "focus_lines": ["economic_research", "infrastructure_spatial"]
            },
            "bright_data_filters": {
                "use_residential_proxies": True,
                "target_country_iso": "RU"
            }
        }
        return structured_parameters

# Тестова демонстрація роботи "мізків"
if __name__ == "__main__":
    agent = ReillyClarifierAgent()
    print(agent.generate_clarification_question("Моніторинг заводу в Саратові"))