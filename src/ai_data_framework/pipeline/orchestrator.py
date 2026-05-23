"""Orquestrador do pipeline analítico."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from ai_data_framework.core.entities import (
    Dataset,
    Hypothesis,
    HypothesisStatus,
    Insight,
    PipelineContext,
)
from ai_data_framework.hypothesis.generator import HypothesisGenerator
from ai_data_framework.ingestion.loaders import get_loader
from ai_data_framework.profiling.analyzer import DataProfiler
from ai_data_framework.validation.validator import HypothesisValidator
from ai_data_framework.visualization.charts import ChartGenerator


class AnalyticsPipeline:
    """Orquestra o fluxo completo de análise."""

    def __init__(self, llm_provider: str = "minimax", **llm_kwargs: Any) -> None:
        self.context = PipelineContext()
        self.llm_provider = llm_provider
        self.llm_kwargs = llm_kwargs

    def load_data(self, source: str, **kwargs: Any) -> Dataset:
        """Etapa 1: Carregar dados."""
        loader = get_loader(source, **kwargs)
        df = loader.load()
        quality = loader.infer_quality(df)

        name = Path(source).stem
        self.context.dataset = Dataset(
            name=name,
            data=df,
            quality=quality,
            metadata={"source": source},
        )
        return self.context.dataset

    def profile_data(self) -> dict[str, Any]:
        """Etapa 2: Analisar estrutura e qualidade."""
        if not self.context.dataset:
            raise ValueError("Dataset não carregado")

        profiler = DataProfiler(self.context.dataset.data)
        quality_metrics = profiler.profile()
        column_stats = {}

        for col in self.context.dataset.schema.names():
            column_stats[col] = profiler.get_column_stats(col)

        # Get correlation matrix
        correlations = profiler.get_correlations()
        correlation_dict = {}
        for pair, corr_val in correlations.items():
            if abs(corr_val) > 0.3:
                correlation_dict[pair] = corr_val

        suggestions = profiler.suggest_hypotheses()

        results = {
            "quality_metrics": quality_metrics,
            "column_stats": column_stats,
            "correlations": correlation_dict,
            "suggestions": suggestions,
        }
        self.context.metadata["profiling"] = results
        return results

    def generate_hypotheses(
        self,
        problem_statement: str | None = None,
        use_llm: bool = True,
    ) -> list[Hypothesis]:
        """Etapa 3: Gerar hipóteses.

        Args:
            problem_statement: Declaração do problema de negócio
            use_llm: Se True, usa LLM para gerar hipóteses automaticamente
        """
        if not self.context.dataset:
            raise ValueError("Dataset não carregado")

        profiler_results = self.context.metadata.get("profiling", {})

        if use_llm and self.llm_provider:
            try:
                from ai_data_framework.llm.client import LLMClient
                llm = LLMClient(provider=self.llm_provider, **self.llm_kwargs)
                llm_hypotheses = llm.generate_hypotheses(
                    problem_statement=problem_statement or "Análise geral de dados",
                    profiling_summary=profiler_results,
                )
                for h_dict in llm_hypotheses:
                    h = Hypothesis(
                        id=h_dict.get("id", f"H{len(self.context.hypotheses) + 1}"),
                        title=h_dict.get("title", ""),
                        description=h_dict.get("description", ""),
                        business_logic=h_dict.get("business_logic", ""),
                        expected_impact=h_dict.get("expected_impact", "Médio"),
                        confidence=h_dict.get("confidence", 0.5),
                        priority=1,
                    )
                    self.context.add_hypothesis(h)

                # Ensure we have minimum 5 hypotheses — use rule-based as supplement
                if len(self.context.hypotheses) < 5:
                    generator = HypothesisGenerator(profiler_results)
                    extra_hyps = generator.generate(problem_statement)
                    existing_ids = {h.id for h in self.context.hypotheses}
                    for h in extra_hyps:
                        if h.id not in existing_ids:
                            self.context.add_hypothesis(h)

                return self.context.hypotheses
            except Exception:
                # Fallback para geração rule-based
                pass

        generator = HypothesisGenerator(profiler_results)
        hypotheses = generator.generate(problem_statement)
        hypotheses = generator.prioritize(hypotheses)

        for h in hypotheses:
            self.context.add_hypothesis(h)

        return hypotheses

    def validate_hypotheses(self) -> list[Hypothesis]:
        """Etapa 4: Validar hipóteses."""
        if not self.context.dataset:
            raise ValueError("Dataset não carregado")

        validator = HypothesisValidator(self.context.dataset.data)
        validated = validator.validate_batch(self.context.hypotheses)
        self.context.hypotheses = validated
        return validated

    def generate_insights(self, use_llm: bool = True) -> list[Insight]:
        """Etapa 5: Gerar insights.

        Args:
            use_llm: Se True, usa LLM para gerar insights enriquecidos
        """
        insights: list[Insight] = []

        if use_llm and self.llm_provider:
            try:
                from ai_data_framework.llm.client import LLMClient
                llm = LLMClient(provider=self.llm_provider, **self.llm_kwargs)
            except Exception:
                llm = None
        else:
            llm = None

        for hypothesis in self.context.get_confirmed_hypotheses():
            insight = self._make_insight(hypothesis, llm=llm)
            insights.append(insight)
            self.context.add_insight(insight)

        # Also generate for partially confirmed (they still have useful info)
        partial = [h for h in self.context.hypotheses if h.status == HypothesisStatus.PARCIALMENTE_CONFIRMADA]
        for hypothesis in partial[:3]:  # top 3 partial
            insight = self._make_insight(hypothesis, llm=llm)
            insights.append(insight)
            self.context.add_insight(insight)

        return insights

    def _make_insight(self, hypothesis: Hypothesis, llm: LLMClient | None = None) -> Insight:
        # Handle both dict and ValidationResult object
        if hypothesis.validation_result:
            if isinstance(hypothesis.validation_result, dict):
                validation_result = hypothesis.validation_result
            else:
                validation_result = {
                    "status": hypothesis.validation_result.status,
                    "confidence": hypothesis.validation_result.confidence,
                    "metrics": hypothesis.validation_result.metrics,
                    "evidence": hypothesis.validation_result.evidence,
                    "limitations": hypothesis.validation_result.limitations,
                }
        else:
            validation_result = {
                "status": hypothesis.status.value,
                "confidence": hypothesis.confidence,
                "metrics": {},
                "evidence": "",
                "limitations": [],
            }

        # Try to use LLM for enriched insights
        if llm is not None:
            try:
                h_dict = hypothesis.to_dict()
                llm_insight = llm.generate_insights(h_dict, validation_result)
                return Insight(
                    hypothesis_id=hypothesis.id,
                    title=llm_insight.get("title", f"Insight: {hypothesis.title}"),
                    description=llm_insight.get("description", hypothesis.description),
                    metrics=llm_insight.get("metrics", validation_result.get("metrics", {})),
                    recommendations=llm_insight.get("recommendations", [f"Validar: {hypothesis.title}"]),
                    business_impact=llm_insight.get("business_impact", hypothesis.expected_impact),
                    confidence=llm_insight.get("confidence", hypothesis.confidence),
                )
            except Exception:
                pass  # Fall back to basic insight

        return Insight(
            hypothesis_id=hypothesis.id,
            title=f"Insight: {hypothesis.title}",
            description=hypothesis.description,
            metrics=validation_result.get("metrics", {}),
            recommendations=[f"Validar: {hypothesis.title}"],
            business_impact=hypothesis.expected_impact,
            confidence=hypothesis.confidence,
        )

    def create_dashboard(self, output_path: str | None = None) -> dict[str, Any]:
        """Etapa 6: Criar dashboard."""
        if not self.context.dataset:
            raise ValueError("Dataset não carregado")

        charts = {}
        chart_gen = ChartGenerator(self.context.dataset.data)

        # Dashboard de qualidade
        if self.context.metadata.get("profiling", {}).get("quality_metrics"):
            qm = self.context.metadata["profiling"]["quality_metrics"]
            charts["quality"] = chart_gen.quality_dashboard(qm)

        # Sumário de hipóteses
        h_list = [h.to_dict() for h in self.context.hypotheses]
        if h_list:
            charts["hypotheses"] = chart_gen.hypothesis_summary(h_list)

        if output_path:
            for name, fig in charts.items():
                fig.write_html(f"{output_path}/{name}_dashboard.html")

        return {name: str(type(fig).__name__) for name, fig in charts.items()}

    def run(
        self,
        source: str,
        problem_statement: str | None = None,
        **kwargs: Any,
    ) -> PipelineContext:
        """Executa o pipeline completo."""
        self.load_data(source, **kwargs)
        self.profile_data()
        self.generate_hypotheses(problem_statement)
        self.validate_hypotheses()
        self.generate_insights()
        return self.context