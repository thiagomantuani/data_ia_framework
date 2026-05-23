"""Analisador de estrutura e qualidade de dados."""

from __future__ import annotations

from typing import Any

import polars as pl

from ai_data_framework.core.entities import DataQualityMetrics


class DataProfiler:
    """Analisa estrutura e qualidade de datasets."""

    def __init__(self, df: pl.LazyFrame) -> None:
        self.df = df

    def profile(self) -> DataQualityMetrics:
        """Executa profiling completo do dataset."""
        collected = self.df.collect()
        schema = self.df.collect_schema()

        null_counts = collected.null_count()
        total_rows = collected.height
        total_cols = collected.width

        null_percent = {
            col: (null_counts[col].item() / total_rows * 100) if total_rows > 0 else 0
            for col in schema.names()
        }

        duplicate_rows = total_rows - collected.unique().height

        completeness = 100 - (sum(null_percent.values()) / len(null_percent) if null_percent else 0)

        return DataQualityMetrics(
            total_rows=total_rows,
            total_columns=total_cols,
            null_percent=null_percent,
            duplicate_rows=duplicate_rows,
            data_types={name: str(dtype) for name, dtype in schema.items()},
            completeness_score=completeness,
        )

    def get_column_stats(self, column: str) -> dict[str, Any]:
        """Estatísticas descritivas de uma coluna."""
        collected = self.df.collect()
        col = collected[column]

        stats: dict[str, Any] = {
            "dtype": str(col.dtype),
            "null_count": col.null_count() if isinstance(col.null_count(), int) else col.null_count().item(),
            "unique_count": col.n_unique(),
        }

        if col.dtype in (pl.Int64, pl.Int32, pl.Float64, pl.Float32):
            mean_val = col.mean() if isinstance(col.mean(), (int, float)) else col.mean().item()
            std_val = col.std() if isinstance(col.std(), (int, float)) else col.std().item()
            min_val = col.min() if isinstance(col.min(), (int, float)) else col.min().item()
            max_val = col.max() if isinstance(col.max(), (int, float)) else col.max().item()
            median_val = col.median() if isinstance(col.median(), (int, float)) else col.median().item()
            q25_val = col.quantile(0.25) if isinstance(col.quantile(0.25), (int, float)) else col.quantile(0.25).item()
            q75_val = col.quantile(0.75) if isinstance(col.quantile(0.75), (int, float)) else col.quantile(0.75).item()

            stats.update({
                "mean": mean_val,
                "std": std_val,
                "min": min_val,
                "max": max_val,
                "median": median_val,
                "q25": q25_val,
                "q75": q75_val,
            })

            # Flag high variance
            if mean_val != 0:
                stats["high_variance"] = std_val / abs(mean_val) > 0.5
            else:
                stats["high_variance"] = std_val > 0

            # Calculate outlier percentage (IQR method)
            iqr = q75_val - q25_val
            if iqr > 0:
                lower = q25_val - 1.5 * iqr
                upper = q75_val + 1.5 * iqr
                outliers = col.filter((col < lower) | (col > upper))
                stats["outliers_pct"] = (outliers.count() / collected.height) * 100
            else:
                stats["outliers_pct"] = 0.0

            # Skewness approximation
            if std_val > 0 and mean_val is not None:
                stats["skewness"] = ((mean_val - median_val) / std_val) * 3 if std_val != 0 else 0
            else:
                stats["skewness"] = 0

        return stats

    def get_correlations(self, numeric_cols: list[str] | None = None) -> dict[str, float]:
        """Calcula correlações entre colunas numéricas."""
        collected = self.df.collect()

        if numeric_cols is None:
            numeric_cols = [
                name for name, dtype in collected.schema.items()
                if dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32)
            ]

        if len(numeric_cols) < 2:
            return {}

        corr_matrix = collected.select(numeric_cols).corr()
        correlations: dict[str, float] = {}

        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i + 1:]:
                key = f"{col1}__{col2}"
                # Extract scalar from correlation DataFrame
                val = corr_matrix.select(col1).to_series()[numeric_cols.index(col2)]
                correlations[key] = val

        return correlations

    def detect_outliers(self, column: str, method: str = "iqr") -> pl.DataFrame:
        """Deteta outliers numa coluna usando IQR ou z-score."""
        collected = self.df.collect()
        col = collected[column]

        if method == "iqr":
            q1 = col.quantile(0.25)
            q3 = col.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            return collected.filter((col < lower) | (col > upper))
        else:
            mean = col.mean()
            std = col.std()
            z_scores = ((col - mean) / std).abs()
            return collected.filter(z_scores > 3)

    def suggest_hypotheses(self) -> list[dict[str, Any]]:
        """Sugere hipóteses iniciais baseadas no profiling."""
        suggestions = []
        collected = self.df.collect()
        schema = self.df.collect_schema()

        for col_name, dtype in schema.items():
            null_pct = (collected[col_name].null_count() if isinstance(collected[col_name].null_count(), int) else collected[col_name].null_count().item()) / collected.height * 100

            if null_pct > 10:
                suggestions.append({
                    "type": "missing_data",
                    "column": col_name,
                    "description": f"Coluna '{col_name}' tem {null_pct:.1f}% de valores nulos",
                    "potential_impact": "Alto" if null_pct > 30 else "Médio",
                })

            if dtype in (pl.Int64, pl.Float64):
                col = collected[col_name]
                std_val = col.std() if isinstance(col.std(), (int, float)) else col.std().item()
                mean_val = col.mean() if isinstance(col.mean(), (int, float)) else col.mean().item()
                if std_val > mean_val * 0.5:
                    suggestions.append({
                        "type": "high_variance",
                        "column": col_name,
                        "description": f"Coluna '{col_name}' tem alta variância (std/mean > 0.5)",
                        "potential_impact": "Médio",
                    })

        return suggestions