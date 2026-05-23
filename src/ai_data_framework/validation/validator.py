"""Validador de hipóteses com testes estatísticos.

Implementa Validation_rules.md — 3 condições para CONFIRMADA:
1. p < 0.05 OU delta > 5% (verificado em cada validador específico)
2. Consistência temporal — ≥2 períodos (adicionado a todas as validações)
3. Evidência quantitativa — ≥2 fontes independentes (adicionado a todas)
"""

from __future__ import annotations

from typing import Any

import polars as pl

from ai_data_framework.core.entities import (
    Hypothesis,
    HypothesisStatus,
    ValidationResult,
)
from ai_data_framework.validation import statistics as stats


class HypothesisValidator:
    """Valida hipóteses numericamente."""

    def __init__(self, df: pl.LazyFrame) -> None:
        self.df = df

    def validate(self, hypothesis: Hypothesis) -> Hypothesis:
        """Valida uma hipótese e atualiza seu status."""
        collected = self.df.collect()

        title_lower = hypothesis.title.lower()
        desc_lower = hypothesis.description.lower()

        if "nulos" in title_lower or "missing" in title_lower or "dados missing" in desc_lower:
            hypothesis = self._validate_missing_data(hypothesis, collected)
        elif "correlação" in title_lower or "correlação" in desc_lower:
            hypothesis = self._validate_correlation(hypothesis, collected)
        elif "variabil" in title_lower or "alta variabilidade" in desc_lower:
            hypothesis = self._validate_variance(hypothesis, collected)
        elif "outlier" in title_lower or "outliers" in desc_lower:
            hypothesis = self._validate_outliers(hypothesis, collected)
        elif "duplic" in title_lower or "duplicada" in desc_lower:
            hypothesis = self._validate_duplicates(hypothesis, collected)
        elif "completude" in title_lower or "completude" in desc_lower:
            hypothesis = self._validate_completeness(hypothesis, collected)
        elif "distribuição" in title_lower or "assimétrica" in desc_lower:
            hypothesis = self._validate_distribution(hypothesis, collected)
        elif "temporal" in title_lower or "sazonal" in desc_lower:
            hypothesis = self._validate_temporal(hypothesis, collected)
        else:
            hypothesis = self._validate_generic(hypothesis, collected)

        # Cross-segment consistency check (Validation_rules.md — REFUTADA condition 2)
        hypothesis = self._validate_cross_segment(hypothesis, collected)

        # Fato-Dimensão validation (exemplo.md — Método Fato-Dimensão)
        hypothesis = self._validate_fact_dimension(hypothesis, collected)

        return hypothesis

    # ─── Helpers para regras 2 e 3 ─────────────────────────────────────────────

    def _get_temporal_depth(self, df: pl.DataFrame) -> int:
        """Retorna número de períodos distintos (colunas temporais detectadas)."""
        date_cols = [
            c for c in df.columns
            if "date" in c.lower() or "time" in c.lower() or "period" in c.lower()
        ]
        if not date_cols:
            # Tenta inferir períodos por linhas distintas
            return max(df.n_unique(), 1)
        depth = 0
        for dc in date_cols:
            depth = max(depth, df[dc].n_unique())
        return depth

    def _count_evidence_sources(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> int:
        """Conta fontes independentes de evidência para a hipótese.

        Cada fonte conta como 1. Fuentes possíveis:
        - missing data (null_pct)
        - correlation signal (r forte/fraco)
        - variance signal (std/mean ratio)
        - outlier signal (outliers_pct)
        - duplicate signal (dup_pct)
        - completeness signal
        - skewness/distribution signal
        - temporal consistency
        """
        sources = 0
        import re

        desc_lower = hypothesis.description.lower()

        # Fonte 1: missing data
        col_match = re.search(r"'(\w+)'", hypothesis.description)
        col = col_match.group(1) if col_match else None
        if col and col in df.columns:
            null_pct = df[col].null_count() / df.height * 100
            if null_pct > 5:
                sources += 1
        elif not col:
            # Check all columns for missing signal
            for c in df.columns:
                if df[c].null_count() / df.height * 100 > 5:
                    sources += 1
                    break

        # Fonte 2: correlation
        match = re.search(r"'(\w+)'.*' (\w+)'", hypothesis.description)
        if match:
            col1, col2 = match.group(1), match.group(2)
            if col1 in df.columns and col2 in df.columns:
                numeric_cols = [
                    c for c in [col1, col2]
                    if df[c].dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32)
                ]
                if len(numeric_cols) == 2:
                    c1 = df[col1].drop_nulls().to_list()
                    c2 = df[col2].drop_nulls().to_list()
                    min_len = min(len(c1), len(c2))
                    c1, c2 = c1[:min_len], c2[:min_len]
                    if len(c1) >= 3:
                        r, p_value = stats.pearson_correlation_pvalue(c1, c2)
                        if abs(r) >= 0.3:
                            sources += 1

        # Fonte 3: variance (std/mean ratio)
        if col and col in df.columns and df[col].dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32):
            values = df[col].drop_nulls().to_list()
            if len(values) >= 3:
                mean_val = sum(values) / len(values)
                if mean_val != 0:
                    std_val = (sum((v - mean_val) ** 2 for v in values) / len(values)) ** 0.5
                    ratio = std_val / abs(mean_val)
                    if ratio > 0.3:
                        sources += 1

        # Fonte 4: outliers
        if col and col in df.columns and df[col].dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32):
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers_pct = df.filter((df[col] < lower) | (df[col] > upper)).height / df.height * 100
            if outliers_pct > 0.5:
                sources += 1

        # Fonte 5: duplicates
        dups = df.height - df.unique().height
        dup_pct = dups / df.height * 100
        if dup_pct > 0.5:
            sources += 1

        # Fonte 6: completeness
        total_nulls = sum(df[c].null_count() for c in df.columns)
        total_cells = df.height * df.width
        completeness = 100 - (total_nulls / total_cells * 100)
        if completeness < 85 or completeness > 95:
            sources += 1

        # Fonte 7: distribution skewness
        if col and col in df.columns and df[col].dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32):
            mean_val = df[col].mean()
            median_val = df[col].median()
            std_val = df[col].std()
            if std_val > 0:
                skewness = abs((mean_val - median_val) / std_val) * 3
                if skewness > 0.3:
                    sources += 1

        # Fonte 8: temporal consistency (if applicable)
        date_cols = [
            c for c in df.columns
            if "date" in c.lower() or "time" in c.lower() or "period" in c.lower()
        ]
        if date_cols:
            numeric_cols = [
                name for name, dtype in df.schema.items()
                if dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32)
                and name != date_cols[0]
            ]
            if numeric_cols:
                values = df.sort(date_cols[0])[numeric_cols[0]].drop_nulls().to_list()
                periods = [f"P{i+1}" for i in range(len(values))]
                if len(values) >= 2:
                    is_consistent, confidence, _ = stats.check_temporal_consistency(
                        values, periods, min_periods=2
                    )
                    if is_consistent and confidence >= 0.6:
                        sources += 1

        return sources

    def _check_metric_temporal_consistency(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
        metric_values: list[float] | None = None,
        metric_col: str | None = None,
    ) -> tuple[bool, float, str]:
        """Verifica consistência temporal de uma métrica específica.

        Args:
            hypothesis: hipótese sendo validada
            df: DataFrame com os dados
            metric_values: valores da métrica por período (se já extraídos)
            metric_col: coluna numérica para extrair valores temporais

        Returns:
            (is_consistent, confidence, explanation)
            - Se não houver colunas temporais: (True, 1.0, "Sem dados temporais")
        """
        date_cols = [
            c for c in df.columns
            if "date" in c.lower() or "time" in c.lower() or "period" in c.lower()
        ]
        if not date_cols:
            return True, 1.0, "Sem colunas temporais — consistência não verificável"

        if metric_values is not None:
            values = metric_values
        elif metric_col and metric_col in df.columns:
            date_col = date_cols[0]
            try:
                values = df.sort(date_col)[metric_col].drop_nulls().to_list()
            except Exception:
                return True, 1.0, "Erro ao extrair valores temporais"
        else:
            # Try to find any numeric column
            numeric_cols = [
                c for c in df.columns
                if df[c].dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32)
                and c not in date_cols
            ]
            if numeric_cols:
                date_col = date_cols[0]
                try:
                    values = df.sort(date_col)[numeric_cols[0]].drop_nulls().to_list()
                except Exception:
                    return True, 1.0, "Erro ao extrair valores temporais"
            else:
                return True, 1.0, "Sem colunas numéricas para análise temporal"

        if len(values) < 2:
            return True, 1.0, "Menos de 2 períodos — consistência temporal não verificável"

        periods = [f"P{i+1}" for i in range(len(values))]
        is_consistent, confidence, explanation = stats.check_temporal_consistency(
            values, periods, min_periods=2
        )
        return is_consistent, confidence, explanation

    def _detect_temporal_columns(self, df: pl.DataFrame) -> list[str]:
        """Detecta colunas temporais no DataFrame."""
        return [
            c for c in df.columns
            if "date" in c.lower() or "time" in c.lower() or "period" in c.lower()
        ]

    def _apply_confirmed_gate(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
        metric_values: list[float] | None = None,
        metric_col: str | None = None,
    ) -> Hypothesis:
        """Aplica as regras 2 (temporal) e 3 (múltiplas fontes) ao resultado.

        Se a regra 1 (p<0.05 OU delta>5%) já foi satisfeita E o status atual é
        CONFIRMADA, verifica também consistência temporal e evidência quantitativa.
        Se qualquer uma das duas falhar, rebaixa para PARCIALMENTE_CONFIRMADA.

        Se não houver dados temporais ou numéricos, NÃO penaliza — apenas documenta
        a limitação (mantém status mas reduz confiança marginalmente).
        """
        if hypothesis.status != HypothesisStatus.CONFIRMADA:
            return hypothesis

        # ─── Regra 2: Consistência Temporal ──────────────────────────────────
        date_cols = self._detect_temporal_columns(df)
        temporal_depth = self._get_temporal_depth(df)

        has_temporal_data = len(date_cols) > 0
        temporal_consistent = True
        temporal_confidence = 1.0
        temporal_explanation = ""

        if has_temporal_data:
            is_consistent, tconf, explanation = self._check_metric_temporal_consistency(
                hypothesis, df, metric_values=metric_values, metric_col=metric_col
            )
            temporal_consistent = is_consistent
            temporal_confidence = tconf
            temporal_explanation = explanation

        has_temporal_consistency = (
            temporal_consistent and temporal_depth >= 2
        ) if has_temporal_data else False  # Sem dados = não verificado, não penaliza

        # ─── Regra 3: Evidência Multi-fonte ──────────────────────────────────
        evidence_sources = self._count_evidence_sources(hypothesis, df)
        has_quantitative_evidence = evidence_sources >= 2

        # ─── Gate Logic ──────────────────────────────────────────────────────
        if has_temporal_data:
            # Temporal data exists: apply strict gate
            if has_temporal_consistency and has_quantitative_evidence:
                # Full compliance — all 3 conditions met
                if hypothesis.validation_result:
                    hypothesis.validation_result["limitations"] = []
                    hypothesis.validation_result["evidence"] += (
                        f" | Temporal: {temporal_depth} períodos ({temporal_explanation}), "
                        f"Fontes: {evidence_sources}"
                    )
                return hypothesis

            if has_temporal_consistency and not has_quantitative_evidence:
                hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                hypothesis.confidence = hypothesis.confidence * 0.8
                if hypothesis.validation_result:
                    hypothesis.validation_result["status"] = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                    hypothesis.validation_result["confidence"] = hypothesis.confidence
                    hypothesis.validation_result["evidence"] = (
                        f"[REBAIXADA] Regras 1 satisfeitas, consistência temporal OK, "
                        f"mas evid. quantitativa insuficiente (fontes={evidence_sources}<2). "
                        f"{hypothesis.validation_result['evidence']}"
                    )
                    hypothesis.validation_result["limitations"] = (
                        hypothesis.validation_result.get("limitations", [])
                        + [f"Evidência quantitativa: {evidence_sources}/2 fontes"]
                    )
                return hypothesis

            if has_quantitative_evidence and not has_temporal_consistency:
                hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                hypothesis.confidence = hypothesis.confidence * 0.8
                if hypothesis.validation_result:
                    hypothesis.validation_result["status"] = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                    hypothesis.validation_result["confidence"] = hypothesis.confidence
                    hypothesis.validation_result["evidence"] = (
                        f"[REBAIXADA] Regras 1 e 3 satisfeitas, mas consistência "
                        f"temporal falhou: {temporal_explanation}. "
                        f"{hypothesis.validation_result['evidence']}"
                    )
                    hypothesis.validation_result["limitations"] = (
                        hypothesis.validation_result.get("limitations", [])
                        + [f"Consistência temporal: {temporal_explanation}"]
                    )
                return hypothesis

            # Both rule 2 and 3 failed
            hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
            hypothesis.confidence = hypothesis.confidence * 0.6
            if hypothesis.validation_result:
                hypothesis.validation_result["status"] = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                hypothesis.validation_result["confidence"] = hypothesis.confidence
                hypothesis.validation_result["evidence"] = (
                    f"[REBAIXADA] Regras 2 e 3 não satisfeitas "
                    f"(temporal: {temporal_explanation}, fontes={evidence_sources}<2). "
                    f"{hypothesis.validation_result['evidence']}"
                )
                hypothesis.validation_result["limitations"] = (
                    hypothesis.validation_result.get("limitations", [])
                    + [
                        f"Consistência temporal: {temporal_explanation}",
                        f"Evidência quantitativa: {evidence_sources}/2 fontes",
                    ]
                )
        else:
            # No temporal data — document limitation, don't penalize
            if has_quantitative_evidence:
                # Rule 3 satisfied, temporal not applicable
                if hypothesis.validation_result:
                    hypothesis.validation_result["limitations"] = (
                        hypothesis.validation_result.get("limitations", [])
                        + ["Consistência temporal: não verificável (sem colunas de data)"]
                    )
                    hypothesis.validation_result["evidence"] += (
                        f" | Fontes: {evidence_sources} | "
                        f"Temporal: não verificável (sem colunas temporais)"
                    )
            else:
                # Neither rule 2 (not applicable) nor rule 3 satisfied
                # But don't fully penalize — mark limitation
                hypothesis.confidence = hypothesis.confidence * 0.85
                if hypothesis.validation_result:
                    hypothesis.validation_result["confidence"] = hypothesis.confidence
                    hypothesis.validation_result["limitations"] = (
                        hypothesis.validation_result.get("limitations", [])
                        + [
                            "Consistência temporal: não verificável (sem colunas de data)",
                            f"Evidência quantitativa: {evidence_sources}/2 fontes",
                        ]
                    )
                    hypothesis.validation_result["evidence"] += (
                        f" | Fontes: {evidence_sources}/2 | "
                        f"Temporal: não verificável (sem colunas temporais)"
                    )

        return hypothesis

    # ─── Validadores específicos ───────────────────────────────────────────────

    def _compute_metric_by_periods(
        self,
        df: pl.DataFrame,
        col: str,
        metric_fn: Any,
    ) -> tuple[list[float], list[str]]:
        """Compute a metric per time period for temporal consistency analysis.

        Args:
            df: DataFrame with data
            col: target column name
            metric_fn: function(period_df, col) -> float

        Returns:
            (metric_values, period_labels) — empty lists if no temporal data
        """
        date_cols = self._detect_temporal_columns(df)
        if not date_cols:
            return [], []

        date_col = date_cols[0]
        try:
            unique_periods = df[date_col].unique().sort().to_list()
        except Exception:
            return [], []

        metrics: list[float] = []
        labels: list[str] = []
        for p in unique_periods:
            try:
                period_df = df.filter(pl.col(date_col) == p)
                if period_df.height > 0 and col in period_df.columns:
                    m = metric_fn(period_df, col)
                    if m is not None:
                        metrics.append(m)
                        labels.append(str(p))
            except Exception:
                continue

        return metrics, labels

    def _integrate_temporal_consistency(
        self,
        hypothesis: Hypothesis,
        metrics: list[float],
        labels: list[str],
    ) -> Hypothesis:
        """Integrate temporal consistency check into hypothesis result.

        If periods >= 2 and inconsistent, downgrades CONFIRMADA → PARCIALMENTE_CONFIRMADA.
        If no temporal data or few periods, documents limitation without penalizing.
        """
        if len(metrics) < 2:
            if hypothesis.status == HypothesisStatus.CONFIRMADA and hypothesis.validation_result:
                hypothesis.validation_result["limitations"] = (
                    hypothesis.validation_result.get("limitations", [])
                    + [f"Consistência temporal: dados insuficientes ({len(metrics)}/{2} períodos)"]
                )
            return hypothesis

        is_consistent, confidence, explanation = stats.check_temporal_consistency(
            metrics, labels, min_periods=2
        )

        if hypothesis.status == HypothesisStatus.CONFIRMADA:
            if is_consistent:
                if hypothesis.validation_result:
                    hypothesis.validation_result["evidence"] += (
                        f" | [TEMPORAL OK] {explanation}"
                    )
                    hypothesis.validation_result.setdefault("limitations", [])
                hypothesis.confidence = min(hypothesis.confidence * 1.05, 0.95)
                if hypothesis.validation_result:
                    hypothesis.validation_result["confidence"] = hypothesis.confidence
            else:
                hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                hypothesis.confidence = hypothesis.confidence * 0.7
                if hypothesis.validation_result:
                    hypothesis.validation_result["status"] = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                    hypothesis.validation_result["confidence"] = hypothesis.confidence
                    hypothesis.validation_result["evidence"] += (
                        f" | [TEMPORAL INCONSISTENTE] {explanation}"
                    )
                    hypothesis.validation_result["limitations"] = (
                        hypothesis.validation_result.get("limitations", [])
                        + [f"Padrão não se mantém temporalmente: {explanation}"]
                    )
        elif hypothesis.status == HypothesisStatus.REFUTADA:
            # For REFUTADA, temporal inconsistency reinforces refutation
            if not is_consistent:
                if hypothesis.validation_result:
                    hypothesis.validation_result["evidence"] += (
                        f" | [TEMPORAL REFORÇA] Padrão também temporalmente inconsistente: {explanation}"
                    )

        return hypothesis

    def _validate_generic(self, hypothesis: Hypothesis, df: pl.DataFrame) -> Hypothesis:
        """Valida hipótese genérica tentando extrair coluna e análise."""
        import re

        match = re.search(r"'(\w+)'", hypothesis.description)
        if not match:
            match = re.search(r"(\w+)", hypothesis.description)

        col_name = match.group(1) if match else None

        if col_name and col_name in df.columns:
            col = df[col_name]
            if col.dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32):
                null_pct = col.null_count() / df.height * 100
                mean_val = col.mean()
                std_val = col.std()
                median_val = col.median()

                confidence = 0.5

                if mean_val != 0 and std_val / abs(mean_val) > 0.5:
                    hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                    confidence = 0.6
                    evidence = f"Coluna '{col_name}' tem alta variabilidade (std/mean = {std_val/abs(mean_val):.2f})"
                elif null_pct > 10:
                    hypothesis.status = HypothesisStatus.CONFIRMADA
                    confidence = min(null_pct / 100, 0.9)
                    evidence = f"Coluna '{col_name}' possui {null_pct:.1f}% de dados missing"
                else:
                    hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                    confidence = 0.5
                    evidence = f"Coluna '{col_name}' validada - sem anomalias críticas detectadas"

                hypothesis.confidence = confidence
                hypothesis.validation_result = ValidationResult(
                    status=hypothesis.status,
                    confidence=confidence,
                    metrics={"null_pct": null_pct, "mean": mean_val, "std": std_val},
                    evidence=evidence,
                    limitations=["Validação automática - análise aprofundada recomendada"],
                )
            else:
                null_pct = col.null_count() / df.height * 100
                unique_pct = col.n_unique() / df.height * 100

                if null_pct > 5:
                    hypothesis.status = HypothesisStatus.CONFIRMADA
                    confidence = min(null_pct / 100, 0.9)
                else:
                    hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                    confidence = 0.4

                hypothesis.confidence = confidence
                hypothesis.validation_result = ValidationResult(
                    status=hypothesis.status,
                    confidence=confidence,
                    metrics={"null_pct": null_pct, "unique_values": unique_pct},
                    evidence=f"Coluna '{col_name}' validada - {null_pct:.1f}% missing, {col.n_unique()} valores únicos",
                    limitations=["Análise categórica limitada"],
                )
        else:
            hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
            hypothesis.confidence = 0.4
            hypothesis.validation_result = ValidationResult(
                status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
                confidence=0.4,
                metrics={},
                evidence="Hipótese requer análise manual para validação completa",
                limitations=["Validação automática não aplicável"],
            )

        # ─── Temporal consistency for generic validator (CONFIRMADA condition 2) ───
        if col_name and col_name in df.columns:
            def _null_pct_fn_generic(period_df: pl.DataFrame, c: str) -> float:
                return period_df[c].null_count() / period_df.height * 100 if period_df.height > 0 else 0.0
            temporal_metrics, temporal_labels = self._compute_metric_by_periods(
                df, col_name, _null_pct_fn_generic
            )
            hypothesis = self._integrate_temporal_consistency(
                hypothesis, temporal_metrics, temporal_labels
            )

        hypothesis = self._apply_confirmed_gate(hypothesis, df)
        return hypothesis

    def _validate_missing_data(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre dados missing."""
        import re

        col_match = re.search(r"'(\w+)'", hypothesis.description)
        col = col_match.group(1) if col_match else None

        if col and col in df.columns:
            null_pct = df[col].null_count() / df.height * 100
            threshold = 20

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
                evidence=f"Coluna '{col}' tem {null_pct:.1f}% de nulos (threshold: {threshold}%)",
                limitations=[],
            )
            hypothesis.status = status
            hypothesis.confidence = confidence

            # ─── Temporal consistency check (Validation_rules.md — CONFIRMADA condition 2) ───
            if col:
                def _null_pct_fn(period_df: pl.DataFrame, c: str) -> float:
                    return period_df[c].null_count() / period_df.height * 100 if period_df.height > 0 else 0.0
                temporal_metrics, temporal_labels = self._compute_metric_by_periods(df, col, _null_pct_fn)
                hypothesis = self._integrate_temporal_consistency(
                    hypothesis, temporal_metrics, temporal_labels
                )

        hypothesis = self._apply_confirmed_gate(hypothesis, df)
        return hypothesis

    def _validate_correlation(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre correlação entre colunas.

        Implementa p-value < 0.05 como threshold estatístico.
        """
        import re

        match = re.search(r"'(\w+)'.*' (\w+)'", hypothesis.description)
        if match:
            col1, col2 = match.group(1), match.group(2)
            if col1 in df.columns and col2 in df.columns:
                numeric_cols = [
                    c for c in [col1, col2]
                    if df[c].dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32)
                ]
                if len(numeric_cols) == 2:
                    c1 = df[col1].drop_nulls().to_list()
                    c2 = df[col2].drop_nulls().to_list()

                    min_len = min(len(c1), len(c2))
                    c1, c2 = c1[:min_len], c2[:min_len]

                    if len(c1) >= 3:
                        r, p_value = stats.pearson_correlation_pvalue(c1, c2)
                        delta_pct = abs(r) * 100

                        if abs(r) > 0.5 and stats.is_significant(p_value):
                            hypothesis.status = HypothesisStatus.CONFIRMADA
                            hypothesis.confidence = min(abs(r), 0.95)
                            hypothesis.validation_result = ValidationResult(
                                status=HypothesisStatus.CONFIRMADA,
                                confidence=hypothesis.confidence,
                                metrics={"correlation": r, "p_value": p_value, "n": min_len, "delta_pct": delta_pct},
                                evidence=f"Correlação forte confirmada: r={r:.3f}, p={p_value:.4f}, delta={delta_pct:.1f}%",
                                limitations=[],
                            )
                        elif abs(r) > 0.3:
                            hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                            hypothesis.confidence = abs(r) * (1 - p_value)
                            hypothesis.validation_result = ValidationResult(
                                status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
                                confidence=hypothesis.confidence,
                                metrics={"correlation": r, "p_value": p_value},
                                evidence=f"Correlação moderada: r={r:.3f}, p={p_value:.4f} (requer validação temporal)",
                                limitations=["Análise temporal necessária para confirmar causalidade"],
                            )

                        # ─── Temporal consistency for correlation (CONFIRMADA condition 2) ───
                        date_cols = self._detect_temporal_columns(df)
                        if date_cols and col1 in df.columns and col2 in df.columns:
                            date_col = date_cols[0]
                            temporal_metrics: list[float] = []
                            temporal_labels: list[str] = []
                            try:
                                for p_val in df[date_col].unique().sort().to_list():
                                    period_df = df.filter(pl.col(date_col) == p_val)
                                    pc1 = period_df[col1].drop_nulls().to_list()
                                    pc2 = period_df[col2].drop_nulls().to_list()
                                    pm = min(len(pc1), len(pc2))
                                    pc1, pc2 = pc1[:pm], pc2[:pm]
                                    if len(pc1) >= 3:
                                        pr, _ = stats.pearson_correlation_pvalue(pc1, pc2)
                                        temporal_metrics.append(pr)
                                        temporal_labels.append(str(p_val))
                            except Exception:
                                pass
                            hypothesis = self._integrate_temporal_consistency(
                                hypothesis, temporal_metrics, temporal_labels
                            )
                    else:
                        # No numeric columns found
                        hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                        hypothesis.confidence = 0.4
                        hypothesis.validation_result = ValidationResult(
                            status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
                            confidence=0.4,
                            metrics={},
                            evidence="Colunas não são numéricas — análise de correlação não aplicável",
                            limitations=["Análise de correlação requer colunas numéricas"],
                        )
                else:
                    # No columns matched pattern
                    hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                    hypothesis.confidence = 0.4
                    hypothesis.validation_result = ValidationResult(
                        status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
                        confidence=0.4,
                        metrics={},
                        evidence="Formato inválido para correlação — use 'coluna1' e 'coluna2'",
                        limitations=["Colunas especificadas não encontradas no dataset"],
                    )

        hypothesis = self._apply_confirmed_gate(hypothesis, df)
        return hypothesis

    def _validate_variance(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre alta variância.

        Implementa Validation_rules.md: CONFIRMADA se:
        - p < 0.05 (significância estatística) OU
        - delta > 5% do baseline (relevância material)
        """
        import re

        col_match = re.search(r"'(\w+)'", hypothesis.description)
        col = col_match.group(1) if col_match else None

        if col and col in df.columns and df[col].dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32):
            values = df[col].drop_nulls().to_list()
            if len(values) < 3:
                hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                hypothesis.confidence = 0.4
                hypothesis.validation_result = ValidationResult(
                    status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
                    confidence=0.4,
                    metrics={},
                    evidence=f"Dados insuficientes para validar variância em '{col}'",
                    limitations=["Amostra pequena demais para teste estatístico"],
                )
                return hypothesis

            mean_val = sum(values) / len(values)
            std_val = (sum((v - mean_val) ** 2 for v in values) / len(values)) ** 0.5

            if mean_val == 0:
                hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                hypothesis.confidence = 0.5
                hypothesis.validation_result = ValidationResult(
                    status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
                    confidence=0.5,
                    metrics={"std": std_val, "mean": mean_val},
                    evidence=f"Coluna '{col}' não pode ser validada (mean=0)",
                    limitations=["Mean zero impede cálculo de significância"],
                )
                return hypothesis

            ratio = std_val / abs(mean_val)
            delta_pct = ratio * 100

            is_material = delta_pct > 5.0
            is_significant_variance = ratio > 0.5

            if is_significant_variance and is_material:
                hypothesis.status = HypothesisStatus.CONFIRMADA
                hypothesis.confidence = min(ratio, 0.9)
                hypothesis.validation_result = ValidationResult(
                    status=HypothesisStatus.CONFIRMADA,
                    confidence=hypothesis.confidence,
                    metrics={"std_mean_ratio": ratio, "delta_pct": delta_pct},
                    evidence=f"Alta variância confirmada: std/mean={ratio:.2f}, delta={delta_pct:.1f}% (>5%)",
                    limitations=[],
                )
                # Temporal consistency for variance
                if col:
                    def _var_ratio_fn(period_df: pl.DataFrame, c: str) -> float | None:
                        vals = period_df[c].drop_nulls().to_list()
                        if len(vals) < 3:
                            return None
                        m = sum(vals) / len(vals)
                        if m == 0:
                            return None
                        s = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5
                        return s / abs(m)
                    temporal_metrics, temporal_labels = self._compute_metric_by_periods(
                        df, col, _var_ratio_fn
                    )
                    hypothesis = self._integrate_temporal_consistency(
                        hypothesis, temporal_metrics, temporal_labels
                    )
                hypothesis = self._apply_confirmed_gate(hypothesis, df)
                return hypothesis
            elif is_significant_variance:
                hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                hypothesis.confidence = ratio * 0.8
                hypothesis.validation_result = ValidationResult(
                    status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
                    confidence=hypothesis.confidence,
                    metrics={"std_mean_ratio": ratio, "delta_pct": delta_pct},
                    evidence=f"Alta variância detectada (std/mean={ratio:.2f}) mas delta={delta_pct:.1f}% ≤ 5%",
                    limitations=["Delta menor que 5% — relevância material duvidosa"],
                )
                # Temporal consistency for variance (partial)
                if col:
                    def _var_ratio_fn2(period_df: pl.DataFrame, c: str) -> float | None:
                        vals = period_df[c].drop_nulls().to_list()
                        if len(vals) < 3:
                            return None
                        m = sum(vals) / len(vals)
                        if m == 0:
                            return None
                        s = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5
                        return s / abs(m)
                    temporal_metrics, temporal_labels = self._compute_metric_by_periods(
                        df, col, _var_ratio_fn2
                    )
                    hypothesis = self._integrate_temporal_consistency(
                        hypothesis, temporal_metrics, temporal_labels
                    )
                hypothesis = self._apply_confirmed_gate(hypothesis, df)
                return hypothesis

        hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
        hypothesis.confidence = 0.5
        hypothesis.validation_result = ValidationResult(
            status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
            confidence=0.5,
            metrics={},
            evidence="Variância dentro de parâmetros normais",
            limitations=["Não há evidência de variabilidade excessiva"],
        )
        hypothesis = self._apply_confirmed_gate(hypothesis, df)
        return hypothesis

    def _validate_outliers(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre outliers."""
        import re

        col_match = re.search(r"'(\w+)'", hypothesis.description)
        col = col_match.group(1) if col_match else None

        if col and col in df.columns and df[col].dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32):
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers = df.filter((df[col] < lower) | (df[col] > upper))
            outliers_pct = outliers.height / df.height * 100
            delta_pct = outliers_pct

            if outliers_pct > 1:
                hypothesis.status = HypothesisStatus.CONFIRMADA
                hypothesis.confidence = min(outliers_pct / 100, 0.9)
            else:
                hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                hypothesis.confidence = min(outliers_pct / 100, 0.9)

            hypothesis.validation_result = ValidationResult(
                status=hypothesis.status,
                confidence=hypothesis.confidence,
                metrics={"outliers_pct": outliers_pct, "delta_pct": delta_pct},
                evidence=f"{outliers_pct:.1f}% dos valores são outliers (IQR method)",
                limitations=[],
            )

            # Temporal consistency for outliers
            if col:
                def _outlier_pct_fn(period_df: pl.DataFrame, c: str) -> float | None:
                    if period_df.height < 4:
                        return None
                    pq1 = period_df[c].quantile(0.25)
                    pq3 = period_df[c].quantile(0.75)
                    piqr = pq3 - pq1
                    if piqr == 0:
                        return 0.0
                    plower = pq1 - 1.5 * piqr
                    pupper = pq3 + 1.5 * piqr
                    p_outliers = period_df.filter(
                        (period_df[c] < plower) | (period_df[c] > pupper)
                    )
                    return p_outliers.height / period_df.height * 100
                temporal_metrics, temporal_labels = self._compute_metric_by_periods(
                    df, col, _outlier_pct_fn
                )
                hypothesis = self._integrate_temporal_consistency(
                    hypothesis, temporal_metrics, temporal_labels
                )

        hypothesis = self._apply_confirmed_gate(hypothesis, df)
        return hypothesis

    def _validate_duplicates(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre dados duplicados."""
        dups = df.height - df.unique().height
        dup_pct = dups / df.height * 100

        if dup_pct > 1:
            hypothesis.status = HypothesisStatus.CONFIRMADA
            hypothesis.confidence = min(dup_pct / 100, 0.9)
        else:
            hypothesis.status = HypothesisStatus.REFUTADA
            hypothesis.confidence = 1.0 - (dup_pct / 100)

        hypothesis.validation_result = ValidationResult(
            status=hypothesis.status,
            confidence=hypothesis.confidence,
            metrics={"duplicate_rows": dups, "dup_pct": dup_pct},
            evidence=f"{dups} linhas duplicadas ({dup_pct:.2f}%)",
            limitations=[],
        )

        # Temporal consistency for duplicates
        date_cols = self._detect_temporal_columns(df)
        if date_cols:
            date_col = date_cols[0]
            temporal_metrics: list[float] = []
            temporal_labels: list[str] = []
            try:
                for p_val in df[date_col].unique().sort().to_list():
                    period_df = df.filter(pl.col(date_col) == p_val)
                    if period_df.height > 0:
                        p_dups = period_df.height - period_df.unique().height
                        p_dup_pct = p_dups / period_df.height * 100
                        temporal_metrics.append(p_dup_pct)
                        temporal_labels.append(str(p_val))
            except Exception:
                pass
            hypothesis = self._integrate_temporal_consistency(
                hypothesis, temporal_metrics, temporal_labels
            )

        hypothesis = self._apply_confirmed_gate(hypothesis, df)
        return hypothesis

    def _validate_completeness(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre completude geral."""
        total_nulls = sum(df[col].null_count() for col in df.columns)
        total_cells = df.height * df.width
        null_pct = (total_nulls / total_cells) * 100
        completeness = 100 - null_pct

        if completeness < 80:
            hypothesis.status = HypothesisStatus.CONFIRMADA
            hypothesis.confidence = min(null_pct / 100, 0.95)
        else:
            hypothesis.status = HypothesisStatus.REFUTADA
            hypothesis.confidence = 1.0 - (null_pct / 100)

        hypothesis.validation_result = ValidationResult(
            status=hypothesis.status,
            confidence=hypothesis.confidence,
            metrics={"completeness_score": completeness, "null_pct": null_pct},
            evidence=f"Completude do dataset: {completeness:.1f}%",
            limitations=[],
        )

        # Temporal consistency for completeness
        date_cols = self._detect_temporal_columns(df)
        if date_cols:
            date_col = date_cols[0]
            temporal_metrics: list[float] = []
            temporal_labels: list[str] = []
            try:
                for p_val in df[date_col].unique().sort().to_list():
                    period_df = df.filter(pl.col(date_col) == p_val)
                    if period_df.height > 0 and period_df.width > 0:
                        p_nulls = sum(period_df[c].null_count() for c in period_df.columns)
                        p_cells = period_df.height * period_df.width
                        p_completeness = 100 - (p_nulls / p_cells * 100) if p_cells > 0 else 100.0
                        temporal_metrics.append(p_completeness)
                        temporal_labels.append(str(p_val))
            except Exception:
                pass
            hypothesis = self._integrate_temporal_consistency(
                hypothesis, temporal_metrics, temporal_labels
            )

        hypothesis = self._apply_confirmed_gate(hypothesis, df)
        return hypothesis

    def _validate_distribution(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre distribuição assimétrica."""
        import re

        col_match = re.search(r"'(\w+)'", hypothesis.description)
        col = col_match.group(1) if col_match else None

        if col and col in df.columns and df[col].dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32):
            mean_val = df[col].mean()
            median_val = df[col].median()
            std_val = df[col].std()

            if std_val > 0:
                skewness = ((mean_val - median_val) / std_val) * 3
                if abs(skewness) > 0.5:
                    hypothesis.status = HypothesisStatus.CONFIRMADA
                    hypothesis.confidence = min(abs(skewness) / 3, 0.9)
                    hypothesis.validation_result = ValidationResult(
                        status=HypothesisStatus.CONFIRMADA,
                        confidence=hypothesis.confidence,
                        metrics={"skewness": skewness},
                        evidence=f"Skewness: {skewness:.2f} (distribuição assimétrica)",
                        limitations=[],
                    )
                    # Temporal consistency for distribution
                    if col:
                        def _skewness_fn(period_df: pl.DataFrame, c: str) -> float | None:
                            vals = period_df[c].drop_nulls().to_list()
                            if len(vals) < 3:
                                return None
                            pm = sum(vals) / len(vals)
                            ps = (sum((v - pm) ** 2 for v in vals) / len(vals)) ** 0.5
                            if ps == 0:
                                return 0.0
                            sorted_vals = sorted(vals)
                            mid = len(sorted_vals) // 2
                            pmed = sorted_vals[mid] if len(sorted_vals) % 2 == 1 else (sorted_vals[mid-1] + sorted_vals[mid]) / 2
                            return ((pm - pmed) / ps) * 3
                        temporal_metrics, temporal_labels = self._compute_metric_by_periods(
                            df, col, _skewness_fn
                        )
                        hypothesis = self._integrate_temporal_consistency(
                            hypothesis, temporal_metrics, temporal_labels
                        )
                    hypothesis = self._apply_confirmed_gate(hypothesis, df)
                    return hypothesis

        hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
        hypothesis.confidence = 0.4
        hypothesis.validation_result = ValidationResult(
            status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
            confidence=0.4,
            metrics={},
            evidence="Distribuição relativamente simétrica",
            limitations=["Análise adicional recomendada"],
        )
        hypothesis = self._apply_confirmed_gate(hypothesis, df)
        return hypothesis

    def _validate_temporal(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre padrões temporais.

        Implementa consistência temporal (≥2 períodos) conforme Validation_rules.md.
        """
        date_cols = [
            c for c in df.columns
            if "date" in c.lower() or "time" in c.lower() or "period" in c.lower()
        ]

        if date_cols:
            date_col = date_cols[0]
            numeric_cols = [
                name for name, dtype in df.schema.items()
                if dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32) and name != date_col
            ]

            if numeric_cols:
                fact_col = numeric_cols[0]
                values = df.sort(date_col)[fact_col].drop_nulls().to_list()
                periods = [f"P{i+1}" for i in range(len(values))]

                if len(values) >= 2:
                    is_consistent, confidence, explanation = stats.check_temporal_consistency(
                        values, periods, min_periods=2
                    )

                    if is_consistent and confidence >= 0.7:
                        hypothesis.status = HypothesisStatus.CONFIRMADA
                        hypothesis.confidence = confidence
                        hypothesis.validation_result = ValidationResult(
                            status=HypothesisStatus.CONFIRMADA,
                            confidence=confidence,
                            metrics={"periods": len(values), "consistency": confidence},
                            evidence=f"Padrão temporal consistente: {explanation}",
                            limitations=[],
                        )
                        hypothesis = self._apply_confirmed_gate(hypothesis, df)
                        return hypothesis
                    elif is_consistent:
                        hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
                        hypothesis.confidence = confidence
                        hypothesis.validation_result = ValidationResult(
                            status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
                            confidence=confidence,
                            metrics={"periods": len(values), "consistency": confidence},
                            evidence=f"Padrão temporal parcial: {explanation}",
                            limitations=["Mais períodos necessários para confirmar"],
                        )
                        hypothesis = self._apply_confirmed_gate(hypothesis, df)
                        return hypothesis
                    else:
                        hypothesis.status = HypothesisStatus.REFUTADA
                        hypothesis.confidence = 1 - confidence
                        hypothesis.validation_result = ValidationResult(
                            status=HypothesisStatus.REFUTADA,
                            confidence=hypothesis.confidence,
                            metrics={"periods": len(values), "consistency": confidence},
                            evidence=f"Padrão temporal inconsistente: {explanation}",
                            limitations=[],
                        )
                        return hypothesis

            hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
            hypothesis.confidence = 0.5
            hypothesis.validation_result = ValidationResult(
                status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
                confidence=0.5,
                metrics={"date_columns": len(date_cols)},
                evidence=f"Colunas temporais detectadas: {date_cols}",
                limitations=["Análise temporal detalhada necessária"],
            )

        else:
            hypothesis.status = HypothesisStatus.PENDENTE
            hypothesis.confidence = 0.0
            hypothesis.validation_result = ValidationResult(
                status=HypothesisStatus.PENDENTE,
                confidence=0.0,
                metrics={},
                evidence="Nenhuma coluna temporal encontrada",
                limitations=["Dados temporais não disponíveis"],
            )
        return hypothesis

    def _validate_fact_dimension(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida os campos Fato-Dimensão da hipótese (exemplo.md — Método Fato-Dimensão).

        Verifica se as colunas fact_metric e dimension existem no DataFrame,
        calcula a métrica agregada por dimensão e adiciona evidências/limitações.

        Se fact_metric for None, pula a validação (compatibilidade com hipóteses sem
        Fato-Dimensão definido).

        Regras:
        - dimension_values definido: filtra/agrega apenas os valores especificados
        - dimension_values não definido: usa todos os valores da dimensão
        - Contribuição % de cada valor da dimensão sobre o total
        - Valida se valores especificados existem no dataset
        """
        # Skip if no fact_metric defined (old hypotheses without Fato-Dimensão)
        if hypothesis.fact_metric is None:
            return hypothesis

        fact_col = hypothesis.fact_metric
        dim_col = hypothesis.dimension
        aggregation = hypothesis.fact_aggregation
        dim_values_filter = hypothesis.dimension_values  # pode ser None

        limitations: list[str] = []

        # ─── Validar existência da coluna fato ──────────────────────────────────
        fact_exists = fact_col in df.columns
        if not fact_exists:
            limitations.append(f"Métrica fato '{fact_col}' não encontrada nos dados")

        # ─── Validar existência da coluna dimensão ──────────────────────────────
        dim_exists = dim_col is not None and dim_col in df.columns
        if dim_col is not None and not dim_exists:
            limitations.append(f"Dimensão '{dim_col}' não encontrada nos dados")

        # ─── Validar dimension_values (valores especificados existem?) ───────────
        missing_dim_values: list[str] = []
        if dim_values_filter and dim_exists:
            available_values = set(df[dim_col].unique().to_list())
            for dv in dim_values_filter:
                if dv not in available_values:
                    missing_dim_values.append(str(dv))

        # ─── Calcular métrica agregada por dimensão ─────────────────────────────
        evidence_parts: list[str] = []
        metrics_out: dict[str, float] = {}

        if fact_exists and (dim_col is None or dim_exists):
            # Mapeamento de agregação para expressões polars
            agg_map = {
                "sum": pl.col(fact_col).sum().alias("fact_value"),
                "avg": pl.col(fact_col).mean().alias("fact_value"),
                "count": pl.col(fact_col).count().alias("fact_value"),
                "min": pl.col(fact_col).min().alias("fact_value"),
                "max": pl.col(fact_col).max().alias("fact_value"),
            }
            agg_label_map = {
                "sum": "Soma",
                "avg": "Média",
                "count": "Contagem",
                "min": "Mínimo",
                "max": "Máximo",
            }

            agg_expr = agg_map.get(aggregation, pl.col(fact_col).sum().alias("fact_value"))
            agg_label = agg_label_map.get(aggregation, aggregation.title())

            if dim_col is not None:
                # Agrupar por dimensão e agregar
                result = (
                    df.group_by(dim_col)
                    .agg(agg_expr)
                    .sort(dim_col)
                )

                # ─── Filtrar por dimension_values se especificado ──────────────────
                if dim_values_filter:
                    result = result.filter(pl.col(dim_col).is_in(dim_values_filter))
                    if missing_dim_values:
                        limitations.append(
                            f"Valores de dimensão não encontrados: {missing_dim_values}"
                        )

                # ─── Calcular contribuição percentual de cada valor ─────────────────
                total_agg = result.select(pl.col("fact_value").sum()).item()
                if total_agg and total_agg != 0:
                    result = result.with_columns(
                        (pl.col("fact_value") / total_agg * 100).alias("contribution_pct")
                    )

                # Construir texto legível com contribuição
                rows: list[str] = []
                contrib_rows: list[str] = []
                for row in result.iter_rows():
                    dim_val, fact_val = row[0], row[1]
                    contrib_pct = None
                    if len(row) > 2:
                        contrib_pct = row[2]

                    if isinstance(fact_val, float):
                        rows.append(f"{dim_val}: {fact_val:.4f}")
                    elif isinstance(fact_val, int):
                        rows.append(f"{dim_val}: {fact_val}")
                    else:
                        rows.append(f"{dim_val}: {fact_val}")

                    if contrib_pct is not None:
                        contrib_rows.append(f"{dim_val}: {contrib_pct:.1f}%")

                # Evidence text
                evidence_parts.append(
                    f"[Fato-Dimensão] {agg_label} de '{fact_col}' por '{dim_col}': {', '.join(rows)}"
                )
                if contrib_rows:
                    evidence_parts.append(f"Contribuição: {', '.join(contrib_rows)}")

                # Metrics
                metrics_out["total_aggregation"] = float(total_agg) if total_agg else 0.0
                metrics_out["unique_dim_values"] = result.height
                metrics_out["dim_values_filtered"] = len(dim_values_filter) if dim_values_filter else result.height

            else:
                # Sem dimensão — agregar toda a coluna fato
                if aggregation == "count":
                    fact_value = df.select(pl.col(fact_col).count()).item()
                else:
                    fact_value = df.select(agg_expr).item()

                if isinstance(fact_value, float):
                    evidence_parts.append(
                        f"[Fato-Dimensão] {agg_label} de '{fact_col}' "
                        f"(sem dimensão): {fact_value:.4f}"
                    )
                    metrics_out["total_aggregation"] = float(fact_value)
                else:
                    evidence_parts.append(
                        f"[Fato-Dimensão] {agg_label} de '{fact_col}' "
                        f"(sem dimensão): {fact_value}"
                    )
                    metrics_out["total_aggregation"] = float(fact_value) if isinstance(fact_value, (int, float)) else 0.0

        # ─── Adicionar métricas fact-dim ao validation_result ──────────────────
        if metrics_out and hypothesis.validation_result:
            existing_metrics = hypothesis.validation_result.get("metrics", {})
            # Prefixar métricas fact-dim para não colidir com métricas existentes
            for k, v in metrics_out.items():
                existing_metrics[f"fd_{k}"] = v
            hypothesis.validation_result["metrics"] = existing_metrics

        # ─── Adicionar limitações ao validation_result ──────────────────────────
        if limitations:
            if hypothesis.validation_result:
                hypothesis.validation_result["limitations"] = (
                    hypothesis.validation_result.get("limitations", [])
                    + limitations
                )
            else:
                # Criar resultado mínimo se não existir
                from ai_data_framework.core.entities import ValidationResult
                hypothesis.validation_result = ValidationResult(
                    status=hypothesis.status,
                    confidence=hypothesis.confidence,
                    metrics={},
                    evidence="",
                    limitations=limitations,
                )

        # ─── Adicionar evidência Fato-Dimensão ──────────────────────────────────
        if evidence_parts:
            if hypothesis.validation_result:
                existing = hypothesis.validation_result.get("evidence", "")
                separator = " | " if existing else ""
                hypothesis.validation_result["evidence"] = existing + separator + " ".join(evidence_parts)

        return hypothesis

    def _validate_cross_segment(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Verifica consistência cross-segment (Validation_rules.md — REFUTADA condition 2).

        Uma hipótese é REFUTADA quando 'a relação observada não se mantém em subperíodos
        ou segmentos diferentes'. Este método detecta comportamento inconsistente entre
        segmentos do dataset (regiões, categorias, períodos, etc.).
        """
        # Find segment/dimension columns
        segment_candidates = [
            "region", "zona", "estado", "cidade", "pais",
            "categoria", "tipo", "produto", "segmento",
            "customer", "cliente", "usuario",
            "year", "month", "trimestre", "semester",
        ]
        segment_cols = [c for c in df.columns if any(k in c.lower() for k in segment_candidates)]

        if not segment_cols:
            return hypothesis  # No segmentation possible — skip

        seg_col = segment_cols[0]

        # Find numeric fact columns (skip date/temporal)
        date_candidates = ["date", "time", "period", "ano", "mês", "mes"]
        fact_cols = [
            c for c in df.columns
            if df[c].dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32)
            and not any(k in c.lower() for k in date_candidates)
        ]

        if not fact_cols:
            return hypothesis

        fact_col = fact_cols[0]

        # Group values by segment
        values_by_segment: dict[str, list[float]] = {}
        for seg_val in df[seg_col].unique().to_list():
            if seg_val is not None:
                vals = df.filter(pl.col(seg_col) == seg_val)[fact_col].drop_nulls().to_list()
                if len(vals) >= 2:  # need at least 2 observations per segment
                    values_by_segment[str(seg_val)] = vals

        if len(values_by_segment) < 2:
            return hypothesis  # Not enough segments to compare

        # Detect direction from primary validation if available
        direction = "any"
        if hypothesis.validation_result and hypothesis.validation_result.get("metrics"):
            metrics = hypothesis.validation_result["metrics"]
            # If correlation or trend detected, use direction
            if "correlation" in metrics:
                direction = "increasing" if metrics["correlation"] > 0 else "decreasing"
            elif "trend" in metrics:
                direction = "increasing" if metrics["trend"] > 0 else "decreasing"

        is_consistent, confidence, explanation = stats.check_cross_segment_consistency(
            values_by_segment, direction=direction
        )

        if not is_consistent:
            # REFUTADA by condition 2: pattern doesn't hold across segments
            hypothesis.status = HypothesisStatus.REFUTADA
            hypothesis.confidence = 1.0
            hypothesis.validation_result = ValidationResult(
                status=HypothesisStatus.REFUTADA,
                confidence=1.0,
                metrics={
                    "segments_compared": len(values_by_segment),
                    "cv": confidence,  # reuse confidence field for CV
                },
                evidence=f"REFUTADA (condição 2): {explanation}",
                limitations=["Comportamento inconsistente entre segmentos — padrão não se replica"],
            )
        elif is_consistent and hypothesis.status == HypothesisStatus.PARCIALMENTE_CONFIRMADA:
            # Upgrade confidence if cross-segment is consistent
            new_confidence = min(hypothesis.confidence + 0.1, 0.95)
            hypothesis.confidence = new_confidence
            if hypothesis.validation_result:
                hypothesis.validation_result["evidence"] += f" | Cross-segment consistente: {explanation}"

        return hypothesis

    def validate_batch(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        """Valida múltiplas hipóteses."""
        return [self.validate(h) for h in hypotheses]
