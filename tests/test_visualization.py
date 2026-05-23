"""Testes para visualization."""

import polars as pl
import pytest

from ai_data_framework.visualization.charts import ChartGenerator


def test_chart_generator_creation():
    """Testa criação do ChartGenerator."""
    df = pl.LazyFrame({"a": [1, 2], "b": [3, 4]})
    cg = ChartGenerator(df)
    assert cg.df is not None


def test_bar_chart():
    """Testa criação de bar chart."""
    df = pl.DataFrame({"x": ["A", "B", "C"], "y": [1, 2, 3]})
    cg = ChartGenerator(df)
    fig = cg.bar_chart(x="x", y="y", title="Test")

    assert fig is not None
    assert len(fig.data) == 1


def test_histogram():
    """Testa criação de histograma."""
    df = pl.DataFrame({"value": [1, 2, 2, 3, 3, 3, 4, 4, 5]})
    cg = ChartGenerator(df)
    fig = cg.histogram(x="value", nbins=5)

    assert fig is not None


def test_scatter():
    """Testa criação de scatter plot."""
    df = pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6], "c": ["A", "B", "A"]})
    cg = ChartGenerator(df)
    fig = cg.scatter(x="x", y="y", color="c")

    assert fig is not None


def test_pie_chart():
    """Testa criação de pie chart."""
    df = pl.DataFrame({"name": ["A", "B", "C"], "value": [10, 20, 30]})
    cg = ChartGenerator(df)
    fig = cg.pie_chart(names="name", values="value")

    assert fig is not None


def test_line_chart():
    """Testa criação de line chart."""
    df = pl.DataFrame({"date": ["2024-01", "2024-02", "2024-03"], "value": [100, 150, 120]})
    cg = ChartGenerator(df)
    fig = cg.line_chart(x="date", y="value")

    assert fig is not None


def test_quality_dashboard():
    """Testa dashboard de qualidade."""
    df = pl.LazyFrame({"a": [1, 2, None], "b": [4, 5, 6]})
    cg = ChartGenerator(df)
    metrics = {"completeness_score": 83.3, "null_percent": {"a": 33.3, "b": 0.0}, "duplicate_rows": 0}
    fig = cg.quality_dashboard(metrics)

    assert fig is not None
    assert len(fig.data) >= 2


def test_hypothesis_summary():
    """Testa sumário de hipóteses."""
    df = pl.LazyFrame({"a": [1, 2]})
    cg = ChartGenerator(df)
    hypotheses = [
        {"status": "CONFIRMADA"},
        {"status": "CONFIRMADA"},
        {"status": "REFUTADA"},
    ]
    fig = cg.hypothesis_summary(hypotheses)

    assert fig is not None


def test_box_plot():
    """Testa box plot."""
    df = pl.DataFrame({"value": [1, 2, 3, 4, 5, 100], "group": ["A", "A", "A", "B", "B", "B"]})
    cg = ChartGenerator(df)
    fig = cg.box_plot(y="value", x="group")

    assert fig is not None


def test_heatmap():
    """Testa heatmap de correlação."""
    df = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})
    cg = ChartGenerator(df)
    fig = cg.heatmap()

    assert fig is not None


def test_kpi_cards():
    """Testa cards de KPI."""
    df = pl.LazyFrame({"a": [1, 2]})
    cg = ChartGenerator(df)
    metrics = {"Revenue": 1000, "Cost": 600, "Margin": 40.0}
    fig = cg.kpi_cards(metrics)

    assert fig is not None
    assert len(fig.data) == 3