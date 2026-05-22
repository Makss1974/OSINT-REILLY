#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY | Block 1 — Data Models
All dataclasses and enums used across the Block 1 pipeline.
Target Directory: /home/ubuntu/IT-PROJECTS/00.Wibe-coding_projects/Wibe_Commander/
Line Length Limit: 100 characters
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class ValidationStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTION = "REJECTION"


class Domain(str, Enum):
    GENERAL = "GENERAL"
    ECONOMIC = "ECONOMIC"
    SOCIO_POLITICAL = "SOCIO_POLITICAL"
    SCIENTIFIC_TECH = "SCIENTIFIC_TECH"
    MILITARY_SECURITY = "MILITARY_SECURITY"
    ECO_LIFE = "ECO_LIFE"


class SearchType(str, Enum):
    QUANTITATIVE = "QUANTITATIVE"      # Таблиці, реєстри, фінанси, декларації
    SEMANTIC = "SEMANTIC"              # Преса, наративи, політичні промови, звіти
    SOCIAL_LISTENING = "SOCIAL_LISTENING"  # Локальні форуми, міські чати, коментарі
    SPATIAL_INFRA = "SPATIAL_INFRA"    # Держтендери, вакансії заводів, гео-вузли


class BrightDataTool(str, Enum):
    WEB_SCRAPER_API = "Web_Scraper_API"
    SERP_API = "SERP_API"
    SCRAPING_BROWSER = "Scraping_Browser"
    WEB_UNLOCKER = "Web_Unlocker"


class Complexity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ─────────────────────────────────────────────
# Stage 1.1 — Validation Data Structures
# ─────────────────────────────────────────────

@dataclass
class ValidationResult:
    status: ValidationStatus
    reason: Optional[str]
    normalized_query: Optional[str]

    def is_approved(self) -> bool:
        return self.status == ValidationStatus.APPROVED

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "normalized_query": self.normalized_query,
        }


# ─────────────────────────────────────────────
# Stage 1.2 — Classification Data Structures
# ─────────────────────────────────────────────

@dataclass
class DomainScore:
    domain: Domain
    confidence: float  # Діапазон ваги: 0.0 – 1.0

    def to_dict(self) -> dict:
        return {"domain": self.domain.value, "confidence": self.confidence}


@dataclass
class ClassificationResult:
    domains: list[DomainScore]
    primary_domain: Domain
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "domains": [d.to_dict() for d in self.domains],
            "primary_domain": self.primary_domain.value,
            "reasoning": self.reasoning,
        }


# ─────────────────────────────────────────────
# Stage 1.3 — Search Plan Data Structures
# ─────────────────────────────────────────────

@dataclass
class SearchTask:
    search_type: SearchType
    bright_data_tool: BrightDataTool
    priority: int               # Пріоритет виконання: 1 = найвищий
    initial_queries: list[str]
    target_domains: list[Domain] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "search_type": self.search_type.value,
            "bright_data_tool": self.bright_data_tool.value,
            "priority": self.priority,
            "initial_queries": self.initial_queries,
            "target_domains": [d.value for d in self.target_domains],
        }


@dataclass
class SearchPlan:
    search_tasks: list[SearchTask]

    def to_dict(self) -> dict:
        return {"search_tasks": [t.to_dict() for t in self.search_tasks]}


# ─────────────────────────────────────────────
# Stage 1.4 — Action Program (Final Output)
# ─────────────────────────────────────────────

@dataclass
class ActionProgram:
    raw_query: str
    normalized_query: str
    primary_domain: Domain
    all_domains: list[DomainScore]
    search_tasks: list[SearchTask]
    estimated_complexity: Complexity
    expected_output_type: str
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "raw_query": self.raw_query,
            "normalized_query": self.normalized_query,
            "primary_domain": self.primary_domain.value,
            "all_domains": [d.to_dict() for d in self.all_domains],
            "search_tasks": [t.to_dict() for t in self.search_tasks],
            "estimated_complexity": self.estimated_complexity.value,
            "expected_output_type": self.expected_output_type,
            "notes": self.notes,
        }


# ─────────────────────────────────────────────
# Rejection Report (Pipeline Exit Matrix)
# ─────────────────────────────────────────────

@dataclass
class RejectionReport:
    raw_query: str
    rejection_reason: str
    stage: str  # Маркер точки зупинки конвеєра, наприклад: "1.1_VALIDATION"

    def to_dict(self) -> dict:
        return {
            "status": "REJECTED",
            "raw_query": self.raw_query,
            "rejection_reason": self.rejection_reason,
            "stage": self.stage,
        }