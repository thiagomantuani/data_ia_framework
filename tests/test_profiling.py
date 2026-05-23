"""Testes para profiling."""

import polars as pl
import pytest

from ai_data_framework.profiling.analyzer import DataProfiler


def test_profiler_creation():
    """Testa criação do profiler."""
    df = pl.LazyFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    profiler = DataProfiler(df)
    assert profiler.df is not None


def test_profile_metrics():
    """Testa métricas de profiling."""
    df = pl.LazyFrame({
        "name": ["A", "B", None, "D"],
        "value": [1, 2, 3, 4],
        "score": [10.0, 20.0, None, 40.0],
    })
    profiler = DataProfiler(df)
    metrics = profiler.profile()

    assert metrics["total_rows"] == 4
    assert metrics["total_columns"] == 3
    assert "name" in metrics["null_percent"]
    assert metrics["null_percent"]["name"] == 25.0  # 1 null in 4 rows


def test_column_stats():
    """Testa estatísticas por coluna."""
    df = pl.LazyFrame({
        "numeric": [1.0, 2.0, 3.0, 4.0, 5.0],
        "category": ["A", "B", "A", "C", "B"],
    })
    profiler = DataProfiler(df)

    stats = profiler.get_column_stats("numeric")
    assert "mean" in stats
    assert stats["mean"] == 3.0
    assert stats["min"] == 1.0
    assert stats["max"] == 5.0


def test_detect_outliers_iqr():
    """Testa detecção de outliers com IQR."""
    df = pl.LazyFrame({"value": [1, 2, 3, 4, 5, 100]})
    profiler = DataProfiler(df)

    outliers = profiler.detect_outliers("value", method="iqr")
    assert outliers.height == 1  # 100 is outlier


def test_suggest_hypotheses():
    """Testa sugestão de hipóteses."""
    df = pl.LazyFrame({
        "normal": [1, 2, 3, 4, 5],
        "high_nulls": [1, None, None, None, 5],
    })
    profiler = DataProfiler(df)
    suggestions = profiler.suggest_hypotheses()

    assert len(suggestions) > 0
    assert any("high_nulls" in s.get("description", "") for s in suggestions)