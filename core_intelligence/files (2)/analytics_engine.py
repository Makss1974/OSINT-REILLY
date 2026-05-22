#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 4 — Analytical Engine (Advisory Council)
Path: core_intelligence/analytics/analytics_engine.py
Line Length Limit: 100 characters

Five-layer analytical framework (per concept.md):
  Layer 1 — Greene   : Root-cause engineering (Baseline Δ, no guessing)
  Layer 2 — Jervis   : Signal vs. noise discrimination (indices over signals)
  Layer 3 — Goldratt : Theory of Constraints (bottleneck detection)
  Layer 4 — Soviet   : Inversion / Silence pattern (anomalous positivity)
  Layer 5 — Causal   : Knowledge graph + probabilistic Markov forecast

Integration contract:
  INPUT  ← CollectionResult dict  (block2_main.py output)
  OUTPUT → AnalyticsResult dict   (passed to Block 5 report builder)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from core_intelligence.router import ReillyLlmRouter

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Advisory prompts  (each layer has its own specialist system prompt)
# ─────────────────────────────────────────────────────────────────────────────

_GREENE_SYSTEM = """
You are Nathanael Greene — Root Cause Engineering Analyst for OSINT-REILLY.

Your method: ZERO guessing. Calculate the mathematical baseline of the target object
from historical norms, then measure ANY deviation (Delta).

When a delta appears, decompose the object as a mechanism — check its four
physical sub-systems: Energy, Raw Materials, Personnel, Logistics.
If the physical constraint is NOT removed in the real world, any positive claim
in the press is automatically marked as FALSE.

Analyze the provided text corpus. Return ONLY valid JSON:
{
  "baseline_established": true | false,
  "detected_deltas": [
    {"subsystem": "Energy|Materials|Personnel|Logistics", "delta_description": "...",
     "severity": "LOW|MEDIUM|HIGH|CRITICAL"}
  ],
  "root_cause_hypothesis": "One sentence, physical cause only.",
  "false_claims_detected": ["claim1", ...],
  "confidence": 0.0
}
"""

_JERVIS_SYSTEM = """
You are Robert Jervis — Signal & Noise Discrimination Analyst for OSINT-REILLY.

Your iron rule: Separate all incoming information into two categories.
SIGNALS (weight = 0): political statements, parade news, propaganda — cheap talk.
INDICES (weight = max): job postings at defense plants, tender sums, customs
declarations, shipping manifests — material traces that are expensive to fake.

Analyze the corpus. Weight every data point. Return ONLY valid JSON:
{
  "signals_identified": [{"text": "...", "source_type": "propaganda|news|statement"}],
  "indices_identified": [
    {"text": "...", "source_type": "vacancy|tender|customs|logistics",
     "value_index": 0.0, "truth_index": 0.0}
  ],
  "overall_noise_ratio": 0.0,
  "key_material_indices": ["top 3 most important indices as strings"]
}
"""

_GOLDRATT_SYSTEM = """
You are Eliyahu Goldratt — Theory of Constraints Analyst for OSINT-REILLY.

Your principle: Every complex system has one or a few BOTTLENECKS that determine
its maximum throughput. Find them.

If the press claims doubled production, look at the physical bottleneck
(imported microchips? engineer shortage? rail logistics?).
If the physical bottleneck has NOT been resolved — the claim is a LIE.

Analyze the corpus. Return ONLY valid JSON:
{
  "identified_bottlenecks": [
    {"name": "...", "type": "supply|personnel|logistics|infrastructure|tech",
     "current_state": "...", "blocks_claim": "claim this bottleneck invalidates"}
  ],
  "system_throughput_assessment": "LOW|MEDIUM|HIGH",
  "contradicted_official_claims": ["claim1", ...],
  "toc_summary": "2-sentence max."
}
"""

_SOVIET_SYSTEM = """
You are the Soviet Pattern Analyst for OSINT-REILLY.
You specialize in reading between the lines of totalitarian or closed-society
discourse. Your two primary detectors:

1. INFORMATION VACUUM: When a strategic topic suddenly vanishes from all news
   channels — this is a strong marker of either a disaster or heavy
   classification. Flag immediately.

2. ANOMALOUS POSITIVITY: When press explodes with patriotic pathos but
   provides ZERO dry numerical data to support it — this is the start of
   a LIE CASCADE. Find the adjacent actions they use to hide the real failure.

Analyze the corpus. Return ONLY valid JSON:
{
  "information_vacuums": [
    {"topic": "...", "last_mention_approximate": "...", "risk_interpretation": "..."}
  ],
  "anomalous_positivity_detected": true | false,
  "lie_cascade_markers": ["marker1", "marker2"],
  "inverted_meaning_findings": [
    {"official_claim": "...", "real_meaning": "..."}
  ],
  "soviet_pattern_summary": "2-sentence max."
}
"""

_MARKOV_SYSTEM = """
You are the Causal AI & Markov Chain Forecasting Engine for OSINT-REILLY.

Based on all prior analytical layers (Greene, Jervis, Goldratt, Soviet Pattern),
model the target system as a finite-state machine and calculate transition
probabilities between states.

States available: STABLE, STRAINED, HIDDEN_CRISIS, PARTIAL_COLLAPSE,
FULL_COLLAPSE, RECOVERING, UNKNOWN.

Produce a 3-step Markov forecast (now → 30 days → 90 days → 180 days).

Return ONLY valid JSON:
{
  "current_state": "STATE_NAME",
  "state_evidence": "Why this state, based on prior layers.",
  "markov_forecast": [
    {"horizon": "30_days",
     "most_likely_state": "STATE_NAME", "probability": 0.0,
     "alternative_states": [{"state": "...", "probability": 0.0}]},
    {"horizon": "90_days",
     "most_likely_state": "STATE_NAME", "probability": 0.0,
     "alternative_states": [{"state": "...", "probability": 0.0}]},
    {"horizon": "180_days",
     "most_likely_state": "STATE_NAME", "probability": 0.0,
     "alternative_states": [{"state": "...", "probability": 0.0}]}
  ],
  "key_trigger_events": ["event that would change the forecast most"],
  "forecast_confidence": 0.0
}
"""

_SYNTHESIS_SYSTEM = """
You are the OSINT-REILLY Chief Synthesis Officer.
You receive structured JSON outputs from five analytical layers and must
produce a concise master intelligence assessment.

Rules:
- Lead with the single most critical finding.
- State contradictions between layers explicitly.
- Assign an overall THREAT_LEVEL: LOW | MEDIUM | HIGH | CRITICAL.
- Keep the executive summary under 150 words.
- Provide 3-5 concrete recommended actions for the operator.

Return ONLY valid JSON:
{
  "executive_summary": "...",
  "critical_finding": "...",
  "threat_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "layer_contradictions": ["..."],
  "recommended_actions": ["action1", "action2", "action3"],
  "analytical_confidence": 0.0
}
"""

_USER_TEMPLATE = (
    "Target query: {query}\n\n"
    "Primary domain: {domain}\n\n"
    "Data corpus (semantic + infrastructure findings):\n{corpus}"
)


# ─────────────────────────────────────────────────────────────────────────────
# AnalyticsEngine
# ─────────────────────────────────────────────────────────────────────────────

class AnalyticsEngine:
    """
    Аналітичне ядро Блоку 4 — Рада Директорів-Аналітиків.

    Запускає п'ять послідовних шарів аналізу, кожен з власним
    спеціалізованим провайдером (через ReillyLlmRouter), та синтезує
    фінальний розвідувальний висновок.

    Шари:
      1. Greene  — пошук першопричин (Groq Llama — швидкий семантичний)
      2. Jervis  — дискримінація сигналів (Groq Llama)
      3. Goldratt— теорія обмежень (Groq Llama)
      4. Soviet  — інверсія/тиша (Groq Llama)
      5. Markov  — ймовірнісний прогноз (OpenRouter DeepSeek — математика)
      Σ Synthesis— головний висновок (Gemini Flash — фінальна редакція)
    """

    def __init__(self, router: ReillyLlmRouter):
        self.router = router

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def analyze(self, collection_result: dict) -> dict:
        """
        Запускає повний п'ятишаровий аналіз CollectionResult.

        Args:
            collection_result: Вихід block2_main.run_block2().

        Returns:
            AnalyticsResult dict з усіма шарами та фінальним синтезом.
        """
        raw_query = collection_result.get("raw_query", "")
        domain    = collection_result.get("primary_domain", "GENERAL")

        logger.info("[Analytics] START | query=%.80s", raw_query)

        # Компактний текстовий корпус для передачі до LLM
        corpus = self._build_corpus(collection_result)
        logger.info("[Analytics] Corpus built | %d chars", len(corpus))

        # ── Шар 1: Greene (Root Cause) ────────────────────────────────────────
        logger.info("[Analytics] Layer 1/5 — Greene (Root Cause)...")
        greene = self._run_layer(
            task_type="semantic_propaganda",
            system=_GREENE_SYSTEM,
            query=raw_query, domain=domain, corpus=corpus,
            layer_name="greene",
        )

        # ── Шар 2: Jervis (Signal Discrimination) ────────────────────────────
        logger.info("[Analytics] Layer 2/5 — Jervis (Signal vs Index)...")
        jervis = self._run_layer(
            task_type="semantic_propaganda",
            system=_JERVIS_SYSTEM,
            query=raw_query, domain=domain, corpus=corpus,
            layer_name="jervis",
        )

        # ── Шар 3: Goldratt (Theory of Constraints) ──────────────────────────
        logger.info("[Analytics] Layer 3/5 — Goldratt (Bottlenecks)...")
        goldratt = self._run_layer(
            task_type="semantic_propaganda",
            system=_GOLDRATT_SYSTEM,
            query=raw_query, domain=domain, corpus=corpus,
            layer_name="goldratt",
        )

        # ── Шар 4: Soviet Pattern (Inversion / Silence) ───────────────────────
        logger.info("[Analytics] Layer 4/5 — Soviet Pattern (Silence/Inversion)...")
        soviet = self._run_layer(
            task_type="semantic_propaganda",
            system=_SOVIET_SYSTEM,
            query=raw_query, domain=domain, corpus=corpus,
            layer_name="soviet",
        )

        # ── Шар 5: Markov / Causal AI ─────────────────────────────────────────
        # Передаємо всі попередні шари як додатковий контекст
        logger.info("[Analytics] Layer 5/5 — Markov Forecast (DeepSeek)...")
        prior_layers_json = json.dumps(
            {"greene": greene, "jervis": jervis,
             "goldratt": goldratt, "soviet": soviet},
            ensure_ascii=False,
        )
        markov_corpus = (
            f"PRIOR ANALYTICAL LAYERS:\n{prior_layers_json}\n\n"
            f"ORIGINAL CORPUS EXCERPT:\n{corpus[:3000]}"
        )
        markov = self._run_layer(
            task_type="math_probabilistic",  # → DeepSeek R1 (математика)
            system=_MARKOV_SYSTEM,
            query=raw_query, domain=domain, corpus=markov_corpus,
            layer_name="markov",
        )

        # ── Синтез (Gemini Flash) ─────────────────────────────────────────────
        logger.info("[Analytics] Synthesis — Chief Officer...")
        synthesis_corpus = json.dumps(
            {"greene": greene, "jervis": jervis, "goldratt": goldratt,
             "soviet": soviet, "markov": markov},
            ensure_ascii=False,
        )
        synthesis = self._run_layer(
            task_type="default",   # → Gemini Flash (фінальна редакція)
            system=_SYNTHESIS_SYSTEM,
            query=raw_query, domain=domain, corpus=synthesis_corpus,
            layer_name="synthesis",
        )

        result = self._build_result(
            raw_query, domain, greene, jervis, goldratt, soviet, markov, synthesis
        )

        threat = result.get("synthesis", {}).get("threat_level", "?")
        conf   = result.get("synthesis", {}).get("analytical_confidence", 0.0)
        logger.info(
            "[Analytics] COMPLETE ✅ | THREAT=%s | confidence=%.2f",
            threat, conf,
        )
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _run_layer(
        self,
        task_type: str,
        system: str,
        query: str,
        domain: str,
        corpus: str,
        layer_name: str,
    ) -> dict:
        """
        Виконує один аналітичний шар через роутер.
        При збої повертає структурований fallback — pipeline не обривається.
        """
        user_msg = _USER_TEMPLATE.format(
            query=query, domain=domain, corpus=corpus[:8000]
        )
        try:
            raw = self.router.execute_query(
                task_type=task_type,
                system_prompt=system,
                user_prompt=user_msg,
            )
            return self._safe_parse(raw, layer_name)
        except Exception as exc:
            logger.error("[Analytics][%s] Router error: %s", layer_name, exc)
            return {"error": str(exc), "layer": layer_name, "status": "FAILED"}

    @staticmethod
    def _safe_parse(text: str, layer_name: str) -> dict:
        """Очищає markdown-феніси та безпечно парсить JSON відповідь."""
        cleaned = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning(
                "[Analytics][%s] JSON parse error: %s | raw=%.60s",
                layer_name, exc, text,
            )
            return {"parse_error": str(exc), "raw_excerpt": text[:200]}

    @staticmethod
    def _build_corpus(collection_result: dict) -> str:
        """
        Стискає CollectionResult у текстовий корпус для LLM.
        Бере ТІЛЬКИ HOT артефакти з infra та direct+counter results із semantic.
        """
        lines = []

        # Семантична секція — прямі та контр-результати
        semantic = collection_result.get("semantic", {})
        for pair in semantic.get("semantic_data", []):
            lines.append(f"[SEMANTIC DIRECT] dork: {pair.get('original_dork','')}")
            for r in pair.get("direct_results", [])[:5]:
                lines.append(f"  → {r.get('title','')} | {r.get('snippet','')[:120]}")
            lines.append(f"[SEMANTIC COUNTER] dork: {pair.get('counter_dork','')}")
            for r in pair.get("counter_results", [])[:5]:
                lines.append(f"  → {r.get('title','')} | {r.get('snippet','')[:120]}")

        # Інфраструктурна секція — лише HOT сигнали
        infra = collection_result.get("infra", {})
        for artifact in infra.get("artifacts", []):
            if artifact.get("status") != "HOT":
                continue
            lines.append(
                f"[INFRA HOT] url={artifact.get('url','')} "
                f"delta={artifact.get('delta_ratio',0):.2%} "
                f"note={artifact.get('notes','')[:100]}"
            )

        return "\n".join(lines) if lines else "No data collected."

    @staticmethod
    def _build_result(
        raw_query: str,
        domain: str,
        greene: dict,
        jervis: dict,
        goldratt: dict,
        soviet: dict,
        markov: dict,
        synthesis: dict,
    ) -> dict:
        return {
            "raw_query":   raw_query,
            "domain":      domain,
            "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "layers": {
                "greene":   greene,
                "jervis":   jervis,
                "goldratt": goldratt,
                "soviet":   soviet,
                "markov":   markov,
            },
            "synthesis": synthesis,
        }
