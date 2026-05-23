"""Gerador de hipóteses de negócio."""

from __future__ import annotations

import uuid
from typing import Any

from ai_data_framework.core.entities import Hypothesis, HypothesisStatus


class HypothesisGenerator:
    """Gera hipóteses de negócio a partir de profiling de dados."""

    def __init__(self, profiling_results: dict[str, Any]) -> None:
        self.profiling = profiling_results

    def generate(self, problem_statement: str | None = None) -> list[Hypothesis]:
        """Gera hipóteses baseadas no profiling e problema declarado."""
        hypotheses = []
        data = self.profiling

        if data.get("quality_metrics", {}).get("null_percent"):
            for col, pct in data["quality_metrics"]["null_percent"].items():
                if pct > 15:
                    hypotheses.append(Hypothesis(
                        id=str(uuid.uuid4())[:8],
                        title=f"Valores nulos em '{col}' afetam métricas",
                        description=f"A coluna '{col}' possui {pct:.1f}% de valores nulos",
                        business_logic=f"Valores em falta em '{col}' podem distorcer análises",
                        expected_impact="Alto" if pct > 30 else "Médio",
                        confidence=0.0,
                        priority=1 if pct > 30 else 2,
                    ))

        if data.get("column_stats"):
            for col, stats in data["column_stats"].items():
                if stats.get("high_variance"):
                    hypotheses.append(Hypothesis(
                        id=str(uuid.uuid4())[:8],
                        title=f"Alta variabilidade em '{col}'",
                        description=f"Desvio padrão elevado detectado em '{col}'",
                        business_logic="Alta variabilidade pode indicar comportamento irregular",
                        expected_impact="Médio",
                        confidence=0.0,
                        priority=3,
                    ))

        if data.get("correlations"):
            for pair, corr in data["correlations"].items():
                if abs(corr) > 0.7:
                    col1, col2 = pair.split("__")
                    hypotheses.append(Hypothesis(
                        id=str(uuid.uuid4())[:8],
                        title=f"Correlação forte entre '{col1}' e '{col2}'",
                        description=f"Correlação de {corr:.2f} entre as colunas",
                        business_logic="Colunas correlacionadas podem indicar redundância ou relação causal",
                        expected_impact="Alto",
                        confidence=0.0,
                        priority=1,
                    ))

        return hypotheses

    def prioritize(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        """Ordena hipóteses por prioridade (impacto + confiança)."""
        return sorted(
            hypotheses,
            key=lambda h: (h.priority, -h.confidence),
        )