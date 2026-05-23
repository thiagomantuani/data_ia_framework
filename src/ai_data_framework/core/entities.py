"""Entidades de domínio do AI Data Framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypedDict

import polars as pl


class HypothesisStatus(str, Enum):
    """Status de validação de uma hipótese."""

    CONFIRMADA = "CONFIRMADA"
    REFUTADA = "REFUTADA"
    PARCIALMENTE_CONFIRMADA = "PARCIALMENTE_CONFIRMADA"
    PENDENTE = "PENDENTE"


class ValidationResult(TypedDict):
    """Resultado da validação de uma hipótese."""

    status: HypothesisStatus
    confidence: float
    metrics: dict[str, float]
    evidence: str
    limitations: list[str]


class DataQualityMetrics(TypedDict):
    """Métricas de qualidade de dados."""

    total_rows: int
    total_columns: int
    null_percent: dict[str, float]
    duplicate_rows: int
    data_types: dict[str, str]
    completeness_score: float


@dataclass(slots=True)
class Dataset:
    """Representa um dataset carregado."""

    name: str
    data: pl.LazyFrame
    quality: DataQualityMetrics
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def schema(self) -> pl.Schema:
        if isinstance(self.data, pl.LazyFrame):
            return self.data.collect_schema()
        return self.data.schema

    @property
    def shape(self) -> tuple[int, int]:
        return (self.quality["total_rows"], self.quality["total_columns"])


@dataclass(slots=True)
class Hypothesis:
    """Representa uma hipótese de negócio."""

    id: str
    title: str
    description: str
    business_logic: str
    expected_impact: str
    confidence: float = 0.0
    status: HypothesisStatus = HypothesisStatus.PENDENTE
    validation_result: ValidationResult | None = None
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.id,
            "title": self.title,
            "description": self.description,
            "business_logic": self.business_logic,
            "expected_impact": self.expected_impact,
            "confidence": self.confidence,
            "status": self.status.value,
            "validation_result": self.validation_result,
            "priority": self.priority,
        }


@dataclass(slots=True)
class Insight:
    """Representa um insight gerado a partir de uma hipótese validada."""

    hypothesis_id: str
    title: str
    description: str
    metrics: dict[str, float]
    recommendations: list[str]
    business_impact: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "title": self.title,
            "description": self.description,
            "metrics": self.metrics,
            "recommendations": self.recommendations,
            "business_impact": self.business_impact,
            "confidence": self.confidence,
        }


@dataclass
class PipelineContext:
    """Contexto compartilhado durante a execução do pipeline."""

    dataset: Dataset | None = None
    hypotheses: list[Hypothesis] = field(default_factory=list)
    insights: list[Insight] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        self.hypotheses.append(hypothesis)

    def add_insight(self, insight: Insight) -> None:
        self.insights.append(insight)

    def get_confirmed_hypotheses(self) -> list[Hypothesis]:
        return [h for h in self.hypotheses if h.status == HypothesisStatus.CONFIRMADA]

    def get_refuted_hypotheses(self) -> list[Hypothesis]:
        return [h for h in self.hypotheses if h.status == HypothesisStatus.REFUTADA]