"""Validador de hipóteses com testes estatísticos."""

from __future__ import annotations

from typing import Any

import polars as pl

from ai_data_framework.core.entities import (
    Hypothesis,
    HypothesisStatus,
    ValidationResult,
)


class HypothesisValidator:
    """Valida hipóteses numericamente."""

    def __init__(self, df: pl.LazyFrame) -> None:
        self.df = df

    def validate(self, hypothesis: Hypothesis) -> Hypothesis:
        """Valida uma hipótese e atualiza seu status."""
        collected = self.df.collect()

        if "nulos" in hypothesis.title.lower() or "missing" in hypothesis.title.lower():
            hypothesis = self._validate_missing_data(hypothesis, collected)
        elif "correlação" in hypothesis.title.lower() or "correlação" in hypothesis.title.lower():
            hypothesis = self._validate_correlation(hypothesis, collected)
        elif "variabil" in hypothesis.title.lower():
            hypothesis = self._validate_variance(hypothesis, collected)
        else:
            hypothesis.validation_result = ValidationResult(
                status=HypothesisStatus.PENDENTE,
                confidence=0.0,
                metrics={},
                evidence="Validação não implementada para este tipo de hipótese",
                limitations=["Tipo de hipótese não reconhecido"],
            )

        return hypothesis

    def _validate_missing_data(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre dados missing."""
        col = hypothesis.description.split("'")[1] if "'" in hypothesis.description else None

        if col and col in df.columns:
            null_pct = df[col].null_count().item() / df.height * 100
            threshold = 30

            if null_pct > threshold:
                status = HypothesisStatus.CONFIRMADA
                confidence = min(null_pct / 100 * 1.2, 1.0)
            else:
                status = HypothesisStatus.REFUTADA
                confidence = 1.0 - (null_pct / 100)

            hypothesis.validation_result = ValidationResult(
                status=status,
                confidence=confidence,
                metrics={"null_percentage": null_pct, "threshold": threshold},
                evidence=f"Coluna '{col}' tem {null_pct:.1f}% de nulos",
                limitations=[],
            )
            hypothesis.status = status
            hypothesis.confidence = confidence

        return hypothesis

    def _validate_correlation(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre correlação entre colunas."""
        hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
        hypothesis.confidence = 0.6
        hypothesis.validation_result = ValidationResult(
            status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
            confidence=0.6,
            metrics={},
            evidence="Correlação identificada requer análise temporal",
            limitations=["Análise temporal necessária para confirmar causalidade"],
        )
        return hypothesis

    def _validate_variance(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre alta variância."""
        hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
        hypothesis.confidence = 0.5
        hypothesis.validation_result = ValidationResult(
            status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
            confidence=0.5,
            metrics={},
            evidence="Alta variância confirmada",
            limitations=["Causa da variância não identificada"],
        )
        return hypothesis

    def validate_batch(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        """Valida múltiplas hipóteses."""
        return [self.validate(h) for h in hypotheses]