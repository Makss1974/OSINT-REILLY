#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | BLOCK 5 — REPORT BUILDER (Конструктор фінальних звітів)
Формує підсумкові документи у форматах JSON, Markdown та HTML на базі матриці аналітики.
Path: /home/ubuntu/IT-PROJECTS/REILLY/block_5_report/report_builder.py
"""

import json
import logging
import os
import sys
import time
from enum import Enum
from typing import Dict, Any, Optional
from block_4_analytics.analytics_engine import AnalyticsResult

# Налаштування відносних імпортів для кореня проекту
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logger = logging.getLogger(__name__)

class ReportFormat(str, Enum):
    JSON     = "json"        # Машинний формат для обміну
    MARKDOWN = "markdown"    # Читабельний репорт для аналітиків
    HTML     = "html"        # Інтерактивні картки для Streamlit UI

class ClassificationLevel(str, Enum):
    PUBLIC      = "PUBLIC // UNCLASSIFIED"
    RESTRICTED  = "RESTRICTED // OSINT INTERNAL"
    SECRET      = "SECRET // REILLY PROPRIETARY"

class GeneratedReport:
    """Об'єкт готового звіту, що містить усі три представлення даних."""
    def __init__(self, report_id: str, query_id: str):
        self.report_id = report_id
        self.query_id = query_id
        self.generated_at = time.time()
        self.classification = ClassificationLevel.RESTRICTED.value
        self.executive_summary = ""
        self.markdown_body = ""
        self.html_body = ""
        self.raw_data: Dict[str, Any] = {}

class Block5ReportBuilder:
    """
    Конструктор звітів Блоку 5. 
    Перетворює математичні висновки на красиві та зрозумілі документи.
    """
    def __init__(self):
        self.default_output_dir = "/home/ubuntu/IT-PROJECTS/REILLY/state/reports"
        os.makedirs(self.default_output_dir, exist_ok=True)

    def build(self, analytics_result: AnalyticsResult) -> GeneratedReport:
        """
        Головний метод збірки звіту. 
        Генерує текстові, машинні та веб-шари документації.
        """
        logger.info("=" * 60)
        logger.info("[Reporter] 📄 БЛОК 5 — REPORT BUILDER | Пакування результатів...")
        logger.info("=" * 60)

        report_id = f"REP_{analytics_result.query_id.split('_')[1] if '_' in analytics_result.query_id else 'DATA'}"
        report = GeneratedReport(report_id, analytics_result.query_id)
        
        # 1. Заповнюємо машинне ядро (JSON)
        report.raw_data = analytics_result.to_dict()
        report.executive_summary = (
            f"Аналітичне дослідження за запитом ID {analytics_result.query_id}. "
            f"Інтегральний коефіцієнт впевненості системи: {round(analytics_result.overall_confidence * 100, 1)}%. "
            f"Виявлено критичних інфраструктурних обмежень: {len(analytics_result.bottlenecks)}."
        )

        # 2. ГЕНЕРАЦІЯ ШАРУ MARKDOWN (Для аналітика)
        logger.info("[Reporter] Збірка текстового шару Markdown...")
        bt_list = "\n".join([f"- **{b}**" for b in analytics_result.bottlenecks])
        report.markdown_body = f"""# 🛡️ OSINT-REILLY INTEGRATED INTELLIGENCE REPORT
**Рівень секретності:** `{report.classification}`
**ID Звіту:** `{report.report_id}` | **ID Запиту:** `{report.query_id}`
**Час генерації:** `{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report.generated_at))}`

---

## 📊 1. ВИКОНАВЧЕ РЕЗЮМЕ
{report.executive_summary}

## 🔍 2. ВИЯВЛЕНІ ВУЗЬКІ МІСЦЯ ІНФРАСТРУКТУРИ (Е. Ґолдратт)
{bt_list if analytics_result.bottlenecks else "- Критичних обмежень ємності не зафіксовано."}

## 🔮 3. ЙМОВІРНІСНИЙ ПРОГНОЗ РЕЖИМУ (А. Марков)
{analytics_result.forecast_summary}

## 💡 4. АДВІЗОРІ-НОТАТКИ ДЛЯ ВАЙБ-КОДЕРА
{analytics_result.advisory_notes}

---
*Generated autonomously by OSINT-REILLY Engine Core v4.0*
"""

        # 3. ГЕНЕРАЦІЯ ШАРУ HTML (Для Streamlit Web UI)
        logger.info("[Reporter] Збірка веб-шару HTML з CSS-стилізацією...")
        bt_html = "".join([f"<li style='color: #ff4b4b; font-weight: bold;'>{b}</li>" for b in analytics_result.bottlenecks])
        
        report.html_body = f"""
        <div style="background-color: #1e1e1e; color: #ffffff; padding: 25px; border-radius: 10px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            <div style="display: flex; justify-content: space-between; border-bottom: 2px solid #333; padding-bottom: 10px;">
                <span style="color: #ff4b4b; font-weight: bold;">🛡️ OSINT-REILLY REPORT</span>
                <span style="background-color: #333; padding: 3px 8px; border-radius: 5px; font-size: 0.8em;">{report.classification}</span>
            </div>
            <p style="font-size: 1.1em; margin-top: 15px;"><strong>Резюме:</strong> {report.executive_summary}</p>
            
            <div style="margin-top: 20px; background-color: #2d2d2d; padding: 15px; border-left: 5px solid #ff4b4b; border-radius: 4px;">
                <h4 style="margin: 0 0 10px 0; color: #ff4b4b;">⚠️ Критичні обмеження (Теорія Обмежень):</h4>
                <ul style="margin: 0; padding-left: 20px;">
                    {bt_html if bt_html else "<li>Обмежень не виявлено</li>"}
                </ul>
            </div>
            
            <div style="margin-top: 15px; background-color: #2d2d2d; padding: 15px; border-left: 5px solid #00a8ff; border-radius: 4px;">
                <h4 style="margin: 0 0 10px 0; color: #00a8ff;">🔮 Марковський прогноз ймовірностей:</h4>
                <p style="margin: 0;">{analytics_result.forecast_summary}</p>
            </div>
            
            <div style="text-align: right; margin-top: 20px; font-size: 0.8em; color: #666;">
                Core ID: {report.report_id} | Engine v4.0
            </div>
        </div>
        """

        logger.info("[Reporter] ✅ Звіт %s успішно спаковано у 3 формати.", report.report_id)
        return report

    def save_report_to_disk(self, generated_report: GeneratedReport, fmt: ReportFormat, custom_dir: Optional[str] = None) -> str:
        """Зберігає обраний формат звіту на диск за стабільними шляхами контуру."""
        target_dir = custom_dir or self.default_output_dir
        os.makedirs(target_dir, exist_ok=True)
        
        filename = f"report_{generated_report.query_id}"
        
        if fmt == ReportFormat.JSON:
            path = os.path.join(target_dir, f"{filename}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(generated_report.raw_data, f, ensure_ascii=False, indent=2)
        elif fmt == ReportFormat.MARKDOWN:
            path = os.path.join(target_dir, f"{filename}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(generated_report.markdown_body)
        elif fmt == ReportFormat.HTML:
            path = os.path.join(target_dir, f"{filename}.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(generated_report.html_body)
        else:
            raise ValueError(f"Невідомий формат звіту: {fmt}")
            
        logger.info("[Reporter] 💾 Файл звіту успішно записано на диск: %s", path)
        return path