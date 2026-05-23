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
    version: int = 1
    created_at: str | None = None
    # Campos Fato-Dimensão (exemplo.md)
    fact_metric: str | None = None       # Coluna da métrica (ex: "valor_venda")
    fact_aggregation: str = "sum"        # Agregação: sum, avg, count, min, max
    dimension: str | None = None         # Coluna da dimensão (ex: "categoria")
    dimension_values: list[str] | None = None  # Valores específicos da dimensão (opcional)

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
            "version": self.version,
            "created_at": self.created_at,
            "fact_metric": self.fact_metric,
            "fact_aggregation": self.fact_aggregation,
            "dimension": self.dimension,
            "dimension_values": self.dimension_values,
        }

    def bump_version(self) -> None:
        """Incrementa versão ao modificar."""
        self.version += 1

    def save(self, path: str | None = None) -> str:
        """Persiste a hipótese em JSON para disco.

        Args:
            path: caminho do arquivo. Se None, usa {id}_v{version}.json.

        Returns:
            Caminho do arquivo escrito.
        """
        import json
        if path is None:
            path = f"{self.id}_v{self.version}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return path

    @classmethod
    def load(cls, path: str) -> Hypothesis:
        """Carrega uma hipótese de um arquivo JSON."""
        import json
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data.pop("hypothesis_id", None)
        return cls(**data)


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
    version: int = 1
    created_at: str | None = None
    # Campos Fato-Dimensão (exemplo.md)
    fact_metric: str | None = None       # Coluna da métrica analisada
    fact_aggregation: str = "sum"        # Agregação usada
    dimension: str | None = None         # Coluna da dimensão analisada

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "title": self.title,
            "description": self.description,
            "metrics": self.metrics,
            "recommendations": self.recommendations,
            "business_impact": self.business_impact,
            "confidence": self.confidence,
            "version": self.version,
            "created_at": self.created_at,
        }

    def bump_version(self) -> None:
        """Incrementa versão ao modificar."""
        self.version += 1

    def save(self, path: str | None = None) -> str:
        """Persiste o insight em JSON para disco.

        Args:
            path: caminho do arquivo. Se None, usa {hypothesis_id}_insight_v{version}.json.

        Returns:
            Caminho do arquivo escrito.
        """
        import json
        if path is None:
            path = f"{self.hypothesis_id}_insight_v{self.version}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return path

    @classmethod
    def load(cls, path: str) -> Insight:
        """Carrega um insight de um arquivo JSON."""
        import json
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)


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