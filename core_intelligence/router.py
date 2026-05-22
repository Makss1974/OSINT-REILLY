#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY: Core LLM Router (Unified OpenAI-compatible interface)
Target Directory: /home/ubuntu/IT-PROJECTS/00.Wibe-coding_projects/Wibe_Commander/
Line Length Limit: 100 characters
"""

import os
import logging
from openai import OpenAI

class ReillyLlmRouter:
    def __init__(self):
        # Зчитування ключів доступу з оточення системи
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")

        # Уніфікована матриця провайдерів (Етап 1.3 Спеціалізація мізків)
        self.providers = {
            "google": {
                "url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                "key": self.gemini_key,
                "model": "gemini-2.5-flash"
            },
            "groq": {
                "url": "https://api.groq.com/openai/v1",
                "key": self.groq_key,
                "model": "llama-3.3-70b-specdec"
            },
            "openrouter": {
                "url": "https://openrouter.ai/api/v1",
                "key": self.openrouter_key,
                "model": "deepseek/deepseek-r1"
            }
        }

    def _get_client(self, provider_name: str) -> tuple:
        """Внутрішній метод створення сумісного OpenAI клієнта."""
        prov = self.providers.get(provider_name)
        if not prov or not prov["key"]:
            logging.warning("Credentials missing for %s. Using fallback.", provider_name)
            return None, None
        
        # Створення стандартного клієнта зі специфічним Base URL провайдера
        client = OpenAI(base_url=prov["url"], api_key=prov["key"])
        return client, prov["model"]

    def execute_query(self, task_type: str, system_prompt: str, user_prompt: str) -> str:
        """
        Роутинг запитів на основі спеціалізації моделей:
        - math_probabilistic -> DeepSeek (через OpenRouter)
        - semantic_propaganda -> Llama 3.3 (через Groq)
        - default/скрапінг -> Gemini (прямий API)
        """
        if task_type == "math_probabilistic":
            provider = "openrouter"
        elif task_type == "semantic_propaganda":
            provider = "groq"
        else:
            provider = "google"

        client, model = self._get_client(provider)
        
        # Захисний каскад: якщо ключі обраного провайдера відсутні, мігруємо на Gemini
        if not client:
            logging.info("Provider %s unavailable. Routing to standard Gemini cluster.", provider)
            client, model = self._get_client("google")
            if not client:
                raise ValueError("Critical error: No active API keys found in environment.")

        try:
            logging.info("Routing query to [%s] using model [%s]...", provider.upper(), model)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2  # Низький показник для максимальної точності аналітики
            )
            return response.choices[0].message.content

        except Exception as e:
            logging.error("API failure on provider %s: %s", provider, str(e))
            
            # Екстрений прорив: якщо Groq чи OpenRouter видали помилку, рятуємо сесію через Gemini
            if provider != "google":
                logging.info("Initiating emergency cascade migration to Gemini cluster...")
                g_client, g_model = self._get_client("google")
                if g_client:
                    res = g_client.chat.completions.create(
                        model=g_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    return res.choices[0].message.content
            raise e

if __name__ == "__main__":
    # Скрипт для локального тест-драйву модуля
    router = ReillyLlmRouter()
    print("LLM Router initialized successfully. Ready for dynamic allocation.")