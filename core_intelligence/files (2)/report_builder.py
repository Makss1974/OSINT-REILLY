#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 5 — Analytical Report Builder
Path: core_intelligence/report/report_builder.py
Line Length Limit: 100 characters

Converts AnalyticsResult (Block 4) into a structured, human-readable
Markdown intelligence report with full factual and logical traceability.

Integration contract:
  INPUT  ← AnalyticsResult dict  (block4_main.py output)
  OUTPUT → ./reports/<timestamp>_reilly_report.md
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from core_intelligence.router import ReillyLlmRouter

logger = logging.getLogger(__name__)

REPORTS_DIR = "./reports"

# ─────────────────────────────────────────────────────────────────────────────
# Report rendering prompt
# ─────────────────────────────────────────────────────────────────────────────

_REPORT_SYSTEM = """
You are the OSINT-REILLY Chief Report Writer.
You receive structured JSON from five analytical layers + a synthesis assessment.
Your task: write a formal OSINT intelligence report in Markdown.

MANDATORY SECTIONS (in this order):
1. ## EXECUTIVE SUMMARY
   - Threat level badge: 🔴 CRITICAL | 🟠 HIGH | 🟡 MEDIUM | 🟢 LOW
   - 3-4 sentences maximum.

2. ## KEY FINDINGS
   - Bullet list of top 5 findings, each traceable to a specific layer.
   - Format: `[LAYER_NAME]` tag before each bullet.

3. ## ROOT CAUSE ANALYSIS  (Greene Layer)
   - Physical subsystems where deltas were detected.
   - Which official claims were falsified and why.

4. ## MATERIAL INDICES VS NOISE  (Jervis Layer)
   - Table: Index | Type | Value Score | Truth Score
   - Overall noise ratio.

5. ## SYSTEM BOTTLENECKS  (Goldratt Layer)
   - Each bottleneck: name, type, what official claim it invalidates.

6. ## INFORMATION WARFARE PATTERNS  (Soviet Layer)
   - Detected vacuums and anomalous positivity events.
   - Inverted meaning table: Official Claim | Real Meaning.

7. ## PROBABILISTIC FORECAST  (Markov Layer)
   - Current state and evidence.
   - Forecast table: Horizon | Most Likely State | Probability
   - Key trigger events.

8. ## RECOMMENDED ACTIONS
   - Numbered list from synthesis.

9. ## METHODOLOGY & CONFIDENCE
   - State which analytical layers were used.
   - Overall confidence score.
   - Data limitations.

RULES:
- Every factual claim must reference its source layer in brackets.
- Do NOT invent data not present in the JSON input.
- Use professional intelligence report language.
- Return the complete Markdown document as plain text (no JSON wrapper).
"""

_REPORT_USER_TEMPLATE = """
Target query: {query}
Domain: {domain}
Collected at: {collected_at}

ANALYTICAL LAYERS JSON:
{layers_json}

SYNTHESIS JSON:
{synthesis_json}

Write the full intelligence report in Markdown.
"""


# ─────────────────────────────────────────────────────────────────────────────
# ReportBuilder
# ─────────────────────────────────────────────────────────────────────────────

class ReportBuilder:
    """
    Будує структурований Markdown-звіт на основі AnalyticsResult.

    Використовує Gemini Flash (default route) для фінальної редакції тексту,
    але також генерує мінімальний структурний звіт без LLM як fallback.
    """

    def __init__(
        self,
        router: ReillyLlmRouter,
        reports_dir: str = REPORTS_DIR,
    ):
        self.router      = router
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)
        logger.info("[ReportBuilder] Ready | reports_dir=%s", reports_dir)

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def build(self, analytics_result: dict, save: bool = True) -> str:
        """
        Генерує повний Markdown-звіт.

        Args:
            analytics_result: Вихід AnalyticsEngine.analyze().
            save:             Якщо True — зберігає .md файл у reports_dir.

        Returns:
            Рядок з повним Markdown-текстом звіту.
        """
        raw_query    = analytics_result.get("raw_query", "")
        domain       = analytics_result.get("domain", "GENERAL")
        analyzed_at  = analytics_result.get("analyzed_at", "")
        layers       = analytics_result.get("layers", {})
        synthesis    = analytics_result.get("synthesis", {})

        logger.info("[ReportBuilder] Building report for query: %.80s", raw_query)

        user_msg = _REPORT_USER_TEMPLATE.format(
            query=raw_query,
            domain=domain,
            collected_at=analyzed_at,
            layers_json=json.dumps(layers, ensure_ascii=False)[:10000],
            synthesis_json=json.dumps(synthesis, ensure_ascii=False),
        )

        try:
            report_md = self.router.execute_query(
                task_type="default",        # Gemini Flash — фінальна редакція
                system_prompt=_REPORT_SYSTEM,
                user_prompt=user_msg,
            )
            logger.info("[ReportBuilder] LLM report generated | %d chars", len(report_md))
        except Exception as exc:
            logger.error("[ReportBuilder] LLM error: %s — using structural fallback.", exc)
            report_md = self._structural_fallback(analytics_result)

        # Додаємо технічний футер трасування
        report_md = self._append_footer(report_md, analytics_result)

        if save:
            filepath = self._save_report(report_md)
            logger.info("[ReportBuilder] Report saved → %s", filepath)

        return report_md

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback (детермінований звіт без LLM)
    # ─────────────────────────────────────────────────────────────────────────

    def _structural_fallback(self, analytics_result: dict) -> str:
        """
        Генерує мінімальний структурний звіт напряму з JSON-даних.
        Використовується якщо LLM-роутер недоступний.
        """
        q   = analytics_result.get("raw_query", "N/A")
        syn = analytics_result.get("synthesis", {})
        tl  = syn.get("threat_level", "UNKNOWN")
        cf  = syn.get("critical_finding", "N/A")
        es  = syn.get("executive_summary", "N/A")
        ra  = syn.get("recommended_actions", [])
        con = syn.get("analytical_confidence", 0.0)

        badge_map = {
            "CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"
        }
        badge = badge_map.get(tl, "⚪")

        layers = analytics_result.get("layers", {})
        greene_rc  = layers.get("greene", {}).get("root_cause_hypothesis", "N/A")
        bottlenecks = layers.get("goldratt", {}).get("identified_bottlenecks", [])
        current_st  = layers.get("markov", {}).get("current_state", "UNKNOWN")
        forecast    = layers.get("markov", {}).get("markov_forecast", [])

        lines = [
            f"# OSINT-REILLY Intelligence Report",
            f"",
            f"**Target**: {q}",
            f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"",
            f"## EXECUTIVE SUMMARY",
            f"{badge} **Threat Level: {tl}**",
            f"",
            f"{es}",
            f"",
            f"## CRITICAL FINDING",
            f"{cf}",
            f"",
            f"## ROOT CAUSE  [Greene]",
            f"{greene_rc}",
            f"",
            f"## BOTTLENECKS  [Goldratt]",
        ]
        for b in bottlenecks:
            lines.append(
                f"- **{b.get('name','?')}** ({b.get('type','?')}): "
                f"{b.get('current_state','')}"
            )
        if not bottlenecks:
            lines.append("- No bottlenecks identified.")

        lines += [
            f"",
            f"## MARKOV FORECAST  [Causal AI]",
            f"Current state: **{current_st}**",
            f"",
            f"| Horizon | State | Probability |",
            f"|---------|-------|-------------|",
        ]
        for f_item in forecast:
            lines.append(
                f"| {f_item.get('horizon','?')} "
                f"| {f_item.get('most_likely_state','?')} "
                f"| {f_item.get('probability', 0.0):.0%} |"
            )

        lines += [
            f"",
            f"## RECOMMENDED ACTIONS",
        ]
        for i, action in enumerate(ra, 1):
            lines.append(f"{i}. {action}")

        lines += [
            f"",
            f"## CONFIDENCE",
            f"Analytical confidence: **{con:.0%}**",
            f"*(Structural fallback report — LLM unavailable)*",
        ]
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _append_footer(report_md: str, analytics_result: dict) -> str:
        """Додає машинно-читабельний футер трасування до кінця звіту."""
        analyzed_at = analytics_result.get("analyzed_at", "")
        domain      = analytics_result.get("domain", "?")
        layers_used = list(analytics_result.get("layers", {}).keys())
        confidence  = (
            analytics_result
            .get("synthesis", {})
            .get("analytical_confidence", 0.0)
        )
        footer = (
            f"\n\n---\n"
            f"*OSINT-REILLY | Generated: {analyzed_at} | "
            f"Domain: {domain} | "
            f"Layers: {', '.join(layers_used)} | "
            f"Confidence: {confidence:.0%}*\n"
        )
        return report_md + footer

    def _save_report(self, report_md: str) -> str:
        """Зберігає звіт у файл з UTC-міткою часу."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename  = f"{timestamp}_reilly_report.md"
        filepath  = os.path.join(self.reports_dir, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report_md)
        except OSError as exc:
            logger.error("[ReportBuilder] Cannot save report: %s", exc)
            return ""
        return filepath
