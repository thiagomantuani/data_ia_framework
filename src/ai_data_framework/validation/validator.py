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
            # Generic validation - try to extract column name and validate
            hypothesis = self._validate_generic(hypothesis, collected)

        return hypothesis

    def _validate_generic(self, hypothesis: Hypothesis, df: pl.DataFrame) -> Hypothesis:
        """Valida hipótese genérica tentando extrair coluna e análise."""
        # Try to extract column name from description
        import re
        # Match quotes
        match = re.search(r"'(\w+)'", hypothesis.description)
        if not match:
            match = re.search(r'(\w+)', hypothesis.description)

        col_name = match.group(1) if match else None

        if col_name and col_name in df.columns:
            col = df[col_name]
            if col.dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32):
                # Numeric column - basic distribution check
                null_pct = col.null_count() / df.height * 100
                mean_val = col.mean()
                std_val = col.std()
                median_val = col.median()

                # Calculate confidence based on data characteristics
                confidence = 0.5

                # Check for high variance
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
                # Non-numeric column
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
            # No column found - generic status
            hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
            hypothesis.confidence = 0.4
            hypothesis.validation_result = ValidationResult(
                status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
                confidence=0.4,
                metrics={},
                evidence="Hipótese requer análise manual para validação completa",
                limitations=["Validação automática não aplicável"],
            )

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

        return hypothesis

    def _validate_correlation(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre correlação entre colunas."""
        import re
        match = re.search(r"'(\w+)'.*' (\w+)'", hypothesis.description)
        if match:
            col1, col2 = match.group(1), match.group(2)
            if col1 in df.columns and col2 in df.columns:
                numeric_cols = [c for c in [col1, col2] if df[c].dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32)]
                if len(numeric_cols) == 2:
                    corr = df.select(numeric_cols).corr()[col1][col2]
                    if abs(corr) > 0.7:
                        hypothesis.status = HypothesisStatus.CONFIRMADA
                        hypothesis.confidence = abs(corr)
                        hypothesis.validation_result = ValidationResult(
                            status=HypothesisStatus.CONFIRMADA,
                            confidence=abs(corr),
                            metrics={"correlation": corr},
                            evidence=f"Correlação forte confirmada: {corr:.3f}",
                            limitations=[],
                        )
                        return hypothesis

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
        import re
        col_match = re.search(r"'(\w+)'", hypothesis.description)
        col = col_match.group(1) if col_match else None

        if col and col in df.columns and df[col].dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32):
            mean_val = df[col].mean()
            std_val = df[col].std()
            if mean_val != 0:
                ratio = std_val / abs(mean_val)
                if ratio > 0.5:
                    hypothesis.status = HypothesisStatus.CONFIRMADA
                    hypothesis.confidence = min(ratio, 0.9)
                    hypothesis.validation_result = ValidationResult(
                        status=HypothesisStatus.CONFIRMADA,
                        confidence=hypothesis.confidence,
                        metrics={"std_mean_ratio": ratio},
                        evidence=f"Alta variância confirmada: std/mean = {ratio:.2f}",
                        limitations=[],
                    )
                    return hypothesis

        hypothesis.status = HypothesisStatus.PARCIALMENTE_CONFIRMADA
        hypothesis.confidence = 0.5
        hypothesis.validation_result = ValidationResult(
            status=HypothesisStatus.PARCIALMENTE_CONFIRMADA,
            confidence=0.5,
            metrics={},
            evidence="Alta variância疑似的",
            limitations=["Causa da variância não identificada"],
        )
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

            hypothesis.status = HypothesisStatus.CONFIRMADA if outliers_pct > 1 else HypothesisStatus.PARCIALMENTE_CONFIRMADA
            hypothesis.confidence = min(outliers_pct / 100, 0.9)
            hypothesis.validation_result = ValidationResult(
                status=hypothesis.status,
                confidence=hypothesis.confidence,
                metrics={"outliers_pct": outliers_pct},
                evidence=f"{outliers_pct:.1f}% dos valores são outliers (IQR method)",
                limitations=[],
            )
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

        hypothesis.status = HypothesisStatus.CONFIRMADA if completeness < 80 else HypothesisStatus.REFUTADA
        hypothesis.confidence = min(null_pct / 100, 0.95)
        hypothesis.validation_result = ValidationResult(
            status=hypothesis.status,
            confidence=hypothesis.confidence,
            metrics={"completeness_score": completeness, "null_pct": null_pct},
            evidence=f"Completude do dataset: {completeness:.1f}%",
            limitations=[],
        )
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
        return hypothesis

    def _validate_temporal(
        self,
        hypothesis: Hypothesis,
        df: pl.DataFrame,
    ) -> Hypothesis:
        """Valida hipótese sobre padrões temporais."""
        # Check for date columns
        date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]

        if date_cols:
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

    def validate_batch(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        """Valida múltiplas hipóteses."""
        return [self.validate(h) for h in hypotheses]