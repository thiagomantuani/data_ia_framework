"""Gerador de hipóteses DATA-DRIVEN — funciona com qualquer dataset."""

from __future__ import annotations

import uuid
from typing import Any

from ai_data_framework.core.entities import Hypothesis, HypothesisStatus


class HypothesisGenerator:
    """Gera hipóteses baseadas EM padrões reais extraídos do dataset fornecido."""

    def __init__(self, profiling_results: dict[str, Any]) -> None:
        self.profiling = profiling_results
        self._col_stats: dict[str, Any] = self.profiling.get("column_stats", {})
        self._quality: dict[str, Any] = self.profiling.get("quality_metrics", {})
        self._corrs: dict[str, float] = self.profiling.get("correlations", {})
        self._fact_col: str = ""
        self._dimension_cols: list[str] = []
        self._analyze_schema()

    def _analyze_schema(self) -> None:
        """Classifica colunas e identifica fato (alvo) vs dimensões."""
        numeric_candidates = []
        cat_cols = []

        for col, stats in self._col_stats.items():
            dtype = str(stats.get("dtype", "")).lower()
            unique = stats.get("unique_count", 0)

            if "int" in dtype or "float" in dtype:
                if col not in ("data_id", "customer_id", "id"):
                    score = stats.get("std", 0) * stats.get("mean", 1)
                    numeric_candidates.append((col, score))
            elif unique > 1 and unique < 100 and "bool" not in dtype:
                cat_cols.append(col)

        numeric_candidates.sort(key=lambda x: x[1], reverse=True)
        if numeric_candidates:
            self._fact_col = numeric_candidates[0][0]

        self._dimension_cols = cat_cols

    def generate(self, problem_statement: str | None = None) -> list[Hypothesis]:
        """Gera hipóteses DIRETAMENTE extraídas dos dados — SEM inventar nada."""
        hypotheses: list[Hypothesis] = []

        hypotheses.extend(self._quality_hypotheses())
        hypotheses.extend(self._correlation_hypotheses())
        if self._col_stats:
            hypotheses.extend(self._dimension_hypotheses())
            hypotheses.extend(self._churn_hypotheses())
            hypotheses.extend(self._outlier_hypotheses())

        return hypotheses[:10]

    def _quality_hypotheses(self) -> list[Hypothesis]:
        hyps = []
        nulls = self._quality.get("null_percent", {})
        total = self._quality.get("total_rows", 1)

        for col, pct in nulls.items():
            if pct > 1:
                hyps.append(Hypothesis(
                    id=str(uuid.uuid4())[:8],
                    title=f"Coluna '{col}' tem {pct:.1f}% de valores ausentes",
                    description=f"Dados missing em '{col}' comprometem análises que dependem dessa variável",
                    business_logic="Investigar causa raiz dos missing antes de usar essa coluna em decisões",
                    expected_impact="Alto" if pct > 10 else "Médio",
                    confidence=min(pct / 100, 0.95),
                    priority=1 if pct > 20 else 3,
                ))

        dup = self._quality.get("duplicate_rows", 0)
        if dup > 0:
            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title=f"Dataset tem {dup} linhas duplicadas ({dup / total * 100:.1f}% do total)",
                description="Linhas duplicadas superestimam métricas e distorcem análises",
                business_logic="Remover duplicatas para garantir integridade dos dados",
                expected_impact="Médio",
                confidence=min(dup / total, 0.9),
                priority=2,
            ))
        return hyps

    def _correlation_hypotheses(self) -> list[Hypothesis]:
        hyps = []
        # Filtrar pares onde ambas colunas são IDs (correlação espúria)
        id_cols = {"id", "data_id", "customer_id", "user_id", "order_id", "product_id"}
        strong = [
            (k, v) for k, v in self._corrs.items()
            if abs(v) > 0.5
            and not (
                k.split("__")[0] in id_cols or k.split("__")[1] in id_cols
            )
        ]
        for pair, corr_val in strong[:6]:
            col1, col2 = pair.split("__")
            direction = "positiva" if corr_val > 0 else "negativa"
            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title=f"Correlação {direction} forte entre '{col1}' e '{col2}' (r={corr_val:.2f})",
                description=f"r={corr_val:.2f} indica que variações em '{col1}' estão fortemente associadas a '{col2}'",
                business_logic=f"Se '{col1}' causa '{col2}': controlar '{col1}' para impactar '{col2}'",
                expected_impact="Médio" if abs(corr_val) < 0.8 else "Alto",
                confidence=abs(corr_val),
                priority=2 if abs(corr_val) > 0.7 else 3,
            ))
        return hyps

    def _dimension_hypotheses(self) -> list[Hypothesis]:
        hyps = []
        if not self._fact_col:
            return hyps

        fact_stats = self._col_stats.get(self._fact_col, {})
        fact_mean = fact_stats.get("mean", 0)

        for dim in self._dimension_cols[:5]:
            dim_stats = self._col_stats.get(dim, {})
            unique = dim_stats.get("unique_count", 0)
            if unique < 2 or unique > 50:
                continue

            title = self._build_dimension_hypothesis(dim)
            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title=title,
                description=f"Variável '{dim}' tem {unique} valores únicos e deve influir em '{self._fact_col}' (média={fact_mean:.1f})",
                business_logic=f"Segmentar análise por '{dim}' para identificar padrões",
                expected_impact="Alto" if unique <= 10 else "Médio",
                confidence=0.65,
                priority=1 if unique <= 5 else 2,
            ))
        return hyps

    def _build_dimension_hypothesis(self, dim: str) -> str:
        dl = dim.lower()
        fc = self._fact_col

        if any(k in dl for k in ["region", "zona", "estado", "cidade", "pais"]):
            return f"'{fc}' varia significativamente por região ('{dim}')"
        if any(k in dl for k in ["categoria", "tipo", "produto", "segmento"]):
            return f"'{fc}' varia por categoria ('{dim}')"
        if any(k in dl for k in ["customer", "cliente", "usuario"]):
            return f"'{fc}' varia por perfil de cliente ('{dim}')"
        if any(k in dl for k in ["status", "estado"]):
            return f"'{fc}' é determinado pelo status ('{dim}')"
        if any(k in dl for k in ["canal", "meio", "origem", "source"]):
            return f"'{fc}' varia conforme canal ('{dim}')"
        if any(k in dl for k in ["dia", "mes", "ano", "week", "day", "month", "year"]):
            return f"'{fc}' varia ao longo do tempo ({dim})"
        if any(k in dl for k in ["satisf", "score", "rating"]):
            return f"'{fc}' correlaciona com score de satisfação ('{dim}')"
        return f"'{fc}' varia conforme '{dim}'"

    def _churn_hypotheses(self) -> list[Hypothesis]:
        hyps = []
        churn_col = next((c for c in self._col_stats if "churn" in c.lower()), None)
        sat_col = next((c for c in self._col_stats
                       if any(k in c.lower() for k in ["satisf", "score", "rating"]) and
                       any(t in str(self._col_stats[c].get("dtype", "")).lower() for t in ("int", "float"))), None)

        if churn_col and sat_col:
            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title=f"Clientes com '{sat_col}' baixo têm maior probabilidade de '{churn_col}'",
                description="Score de satisfação é preditor known de churn — clientes com score abaixo da média tendem a churnar mais",
                business_logic="Priorizar ações de retention em clientes com score baixo",
                expected_impact="Alto",
                confidence=0.75,
                priority=1,
            ))
        return hyps

    def prioritize(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        """Ordena hipóteses por prioridade (menor número = mais importante)."""
        return sorted(hypotheses, key=lambda h: (h.priority, -h.confidence))

    def _outlier_hypotheses(self) -> list[Hypothesis]:
        hyps = []
        for col, stats in self._col_stats.items():
            if stats.get("high_variance") and col not in ("data_id", "customer_id"):
                hyps.append(Hypothesis(
                    id=str(uuid.uuid4())[:8],
                    title=f"Coluna '{col}' tem alta variabilidade — investigar outliers",
                    description=f"std/mean elevado indica presença de outliers ou subgrupos distintos em '{col}'",
                    business_logic="Analisar distribuição de '{col}' por segmentos antes de usar em decisões",
                    expected_impact="Médio",
                    confidence=0.55,
                    priority=3,
                ))
        return hyps