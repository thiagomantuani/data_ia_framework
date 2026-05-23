"""Orquestrador do pipeline analítico."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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

    def __init__(
        self,
        llm_provider: str = "minimax",
        api_key: str | None = None,
        audit_output_dir: str | None = None,
        hypotheses_output_dir: str | None = None,
        **llm_kwargs: Any,
    ) -> None:
        from ai_data_framework.audit import AuditLogger

        self.context = PipelineContext()
        self.llm_provider = llm_provider
        self._api_key = api_key
        self.llm_kwargs = llm_kwargs
        self._audit = AuditLogger(output_dir=audit_output_dir)
        self._hypotheses_output_dir = hypotheses_output_dir or str(Path.home() / ".ai-data" / "hypotheses")
        self.context.metadata["audit"] = self._audit

    def load_data(self, source: str, **kwargs: Any) -> Dataset:
        """Etapa 1: Carregar dados."""
        from ai_data_framework.audit import OperationType

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

        self._audit.log(
            operation=OperationType.LOAD,
            input_data={"source": source, "options": kwargs},
            output_data={
                "name": name,
                "rows": quality.get("total_rows", 0),
                "cols": quality.get("total_columns", 0),
                "completeness": quality.get("completeness_score", 0),
            },
            metadata={"loader": type(loader).__name__},
        )

        return self.context.dataset

    def profile_data(self) -> dict[str, Any]:
        """Etapa 2: Analisar estrutura e qualidade."""
        from ai_data_framework.audit import OperationType

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

        self._audit.log(
            operation=OperationType.PROFILE,
            input_data={"dataset": self.context.dataset.name},
            output_data={
                "cols_analyzed": len(column_stats),
                "completeness": quality_metrics.get("completeness_score", 0),
                "correlations_found": len(correlation_dict),
                "suggestions": len(suggestions),
            },
        )

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
        from ai_data_framework.audit import OperationType

        if not self.context.dataset:
            raise ValueError("Dataset não carregado")

        profiler_results = self.context.metadata.get("profiling", {})
        hyps_count = 0

        if use_llm and self.llm_provider:
            try:
                from ai_data_framework.llm.client import LLMClient
                llm = LLMClient(provider=self.llm_provider, api_key=self._api_key, **self.llm_kwargs)
                # Only use LLM if we have real credentials
                has_creds = bool(llm.client.api_key)
                if hasattr(llm.client, 'group_id'):
                    has_creds = has_creds and bool(llm.client.group_id)
                if has_creds:
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
                            fact_metric=h_dict.get("fact_metric"),
                            fact_aggregation=h_dict.get("fact_aggregation", "sum"),
                            dimension=h_dict.get("dimension"),
                            dimension_values=h_dict.get("dimension_values"),
                        )
                        self.context.add_hypothesis(h)
                else:
                    # No API keys — skip LLM entirely, fall through to data-driven
                    pass
            except Exception:
                # Fallback para geração rule-based
                pass

        # If no hypotheses yet (no LLM or LLM failed), use data-driven generator
        if not self.context.hypotheses:
            generator = HypothesisGenerator(profiler_results)
            hypotheses = generator.generate(problem_statement)
            hypotheses = generator.prioritize(hypotheses)
            for h in hypotheses:
                self.context.add_hypothesis(h)
        else:
            # Ensure we have minimum 5 hypotheses — use rule-based as supplement
            if len(self.context.hypotheses) < 5:
                generator = HypothesisGenerator(profiler_results)
                extra_hyps = generator.generate(problem_statement)
                # Deduplicate by title to avoid duplicate hypotheses from LLM fallback
                existing_titles = {h.title for h in self.context.hypotheses}
                for h in extra_hyps:
                    if h.title not in existing_titles:
                        self.context.add_hypothesis(h)

        hyps_count = len(self.context.hypotheses)

        self._audit.log(
            operation=OperationType.GENERATE_HYPOTHESIS,
            input_data={"problem_statement": problem_statement, "use_llm": use_llm},
            output_data={
                "count": hyps_count,
                "priorities": [h.priority for h in self.context.hypotheses],
            },
        )

        return self.context.hypotheses

    def validate_hypotheses(self) -> list[Hypothesis]:
        """Etapa 4: Validar hipóteses."""
        from ai_data_framework.audit import OperationType

        if not self.context.dataset:
            raise ValueError("Dataset não carregado")

        validator = HypothesisValidator(self.context.dataset.data)
        validated = validator.validate_batch(self.context.hypotheses)
        self.context.hypotheses = validated

        status_counts: dict[str, int] = {}
        for h in validated:
            key = h.status.value
            status_counts[key] = status_counts.get(key, 0) + 1

        self._audit.log(
            operation=OperationType.VALIDATE_HYPOTHESIS,
            input_data={"total": len(validated)},
            output_data=status_counts,
        )

        return validated

    def generate_insights(self, use_llm: bool = True) -> list[Insight]:
        """Etapa 5: Gerar insights.

        Args:
            use_llm: Se True, usa LLM para gerar insights enriquecidos
        """
        from ai_data_framework.audit import OperationType

        insights: list[Insight] = []

        if use_llm and self.llm_provider:
            try:
                from ai_data_framework.llm.client import LLMClient
                llm = LLMClient(provider=self.llm_provider, api_key=self._api_key, **self.llm_kwargs)
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

        self._audit.log(
            operation=OperationType.GENERATE_INSIGHT,
            input_data={"use_llm": use_llm},
            output_data={
                "count": len(insights),
                "confirmed": len([h for h in self.context.get_confirmed_hypotheses()]),
                "partial": len(partial[:3]),
            },
        )

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
        from ai_data_framework.audit import OperationType

        if not self.context.dataset:
            raise ValueError("Dataset não carregado")

        charts = {}
        source = self.context.dataset.metadata.get("source", self.context.dataset.name)
        chart_gen = ChartGenerator(
            self.context.dataset.data,
            source=source,
            period=None,  # TODO: infer from date column
        )

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

        self._audit.log(
            operation=OperationType.CREATE_DASHBOARD,
            input_data={"output_path": output_path},
            output_data={name: str(type(fig).__name__) for name, fig in charts.items()},
        )

        return {name: str(type(fig).__name__) for name, fig in charts.items()}

    def export_audit_log(self, path: str | None = None) -> str:
        """Exporta o log de auditoria para JSON.

        Returns:
            Caminho do arquivo escrito.
        """
        return self._audit.export_json(path)

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
        self._persist_hypotheses_and_insights()
        self.export_audit_log()
        return self.context

    def _persist_hypotheses_and_insights(self) -> None:
        """Persiste hipóteses e insights em disco ao final do pipeline."""
        if self._hypotheses_output_dir is None:
            return
        from pathlib import Path

        out_dir = Path(self._hypotheses_output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        for h in self.context.hypotheses:
            h.save(str(out_dir / f"{h.id}_v{h.version}.json"))

        for ins in self.context.insights:
            ins.save(str(out_dir / f"{ins.hypothesis_id}_insight_v{ins.version}.json"))
