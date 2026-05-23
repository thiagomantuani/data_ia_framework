"""Testes para core entities."""

import polars as pl
import pytest

from ai_data_framework.core.entities import (
    Dataset,
    DataQualityMetrics,
    Hypothesis,
    HypothesisStatus,
    Insight,
)


def test_hypothesis_creation():
    h = Hypothesis(
        id="H1",
        title="Test Hypothesis",
        description="Test description",
        business_logic="Test logic",
        expected_impact="Alto",
    )
    assert h.id == "H1"
    assert h.status == HypothesisStatus.PENDENTE
    assert h.confidence == 0.0


def test_hypothesis_to_dict():
    h = Hypothesis(
        id="H1",
        title="Test",
        description="Test",
        business_logic="Test",
        expected_impact="Alto",
    )
    d = h.to_dict()
    assert d["hypothesis_id"] == "H1"
    assert d["status"] == "PENDENTE"


def test_dataset_shape():
    quality = DataQualityMetrics(
        total_rows=100,
        total_columns=5,
        null_percent={},
        duplicate_rows=0,
        data_types={},
        completeness_score=100.0,
    )
    df = pl.LazyFrame({"a": [1, 2, 3]})
    ds = Dataset(name="test", data=df, quality=quality)
    assert ds.shape == (100, 5)


def test_pipeline_context_hypotheses():
    from ai_data_framework.core.entities import PipelineContext

    ctx = PipelineContext()
    h = Hypothesis(
        id="H1",
        title="Test",
        description="Test",
        business_logic="Test",
        expected_impact="Alto",
    )
    ctx.add_hypothesis(h)
    assert len(ctx.hypotheses) == 1
    assert len(ctx.get_confirmed_hypotheses()) == 0