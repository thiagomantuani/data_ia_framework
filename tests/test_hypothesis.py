"""Testes para hypothesis generator."""

import pytest

from ai_data_framework.hypothesis.generator import HypothesisGenerator
from ai_data_framework.core.entities import Hypothesis


def test_generator_creation():
    """Testa criação do generator."""
    profiling = {"quality_metrics": {"null_percent": {}}}
    gen = HypothesisGenerator(profiling)
    assert gen.profiling == profiling


def test_generate_hypotheses_from_nulls():
    """Testa geração de hipóteses sobre nulos."""
    profiling = {
        "quality_metrics": {
            "null_percent": {
                "col_a": 35.0,
                "col_b": 5.0,
            }
        }
    }
    gen = HypothesisGenerator(profiling)
    hypotheses = gen.generate()

    assert len(hypotheses) >= 1
    assert any("col_a" in h.title for h in hypotheses)


def test_generate_from_correlations():
    """Testa geração de hipóteses sobre correlações."""
    profiling = {
        "quality_metrics": {},
        "correlations": {
            "A__B": 0.85,
            "C__D": 0.3,
        }
    }
    gen = HypothesisGenerator(profiling)
    hypotheses = gen.generate()

    assert len(hypotheses) >= 1
    assert any("A" in h.title and "B" in h.title for h in hypotheses)


def test_prioritize():
    """Testa priorização de hipóteses."""
    profiling = {"quality_metrics": {"null_percent": {}}}
    gen = HypothesisGenerator(profiling)

    h1 = Hypothesis(
        id="1", title="Low", description="", business_logic="", expected_impact="Baixo", priority=3
    )
    h2 = Hypothesis(
        id="2", title="High", description="", business_logic="", expected_impact="Alto", priority=1
    )
    h3 = Hypothesis(
        id="3", title="Medium", description="", business_logic="", expected_impact="Médio", priority=2
    )

    prioritized = gen.prioritize([h1, h2, h3])
    assert prioritized[0].priority == 1
    assert prioritized[1].priority == 2
    assert prioritized[2].priority == 3