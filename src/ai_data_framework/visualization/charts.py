"""Gerador de gráficos e dashboards."""

from __future__ import annotations

from pathlib import Path


import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import polars as pl


class ChartGenerator:
    """Gera visualizações a partir de dados."""

    def __init__(self, df: pl.LazyFrame | pl.DataFrame, source: str | None = None, period: str | None = None) -> None:
        self.df = df
        self.source = source
        self.period = period

    def _collect(self) -> pl.DataFrame:
        """Helper para coletar LazyFrame."""
        return self.df.collect() if isinstance(self.df, pl.LazyFrame) else self.df

    def _add_metadata(self, fig: go.Figure, source: str | None = None, period: str | None = None) -> go.Figure:
        """Adiciona fonte e período ao gráfico como annotation."""
        src = source or self.source or ""
        prd = period or self.period or ""

        notes = []
        if src:
            notes.append(f"Fonte: {src}")
        if prd:
            notes.append(f"Período: {prd}")

        if notes:
            fig.add_annotation(
                text=" | ".join(notes),
                xref="paper", yref="paper",
                x=1, y=-0.15,
                showarrow=False,
                font=dict(size=10, color="gray"),
                align="right",
            )

        return fig

    def bar_chart(
        self,
        x: str,
        y: str,
        title: str = "",
        color: str | None = None,
        orientation: str = "v",
        source: str | None = None,
        period: str | None = None,
    ) -> go.Figure:
        """Cria gráfico de barras com metadata."""
        data = self._collect()
        fig = px.bar(
            data,
            x=x,
            y=y,
            color=color,
            title=title,
            orientation=orientation if orientation == "h" else None,
        )
        fig = self._add_metadata(fig, source=source, period=period)
        fig.update_layout(template="plotly_dark", margin=dict(l=40, r=40, t=60, b=40))
        return fig

    def histogram(
        self,
        x: str,
        title: str = "",
        nbins: int = 30,
        color: str | None = None,
        source: str | None = None,
        period: str | None = None,
    ) -> go.Figure:
        """Cria histograma."""
        data = self._collect()
        fig = px.histogram(data, x=x, nbins=nbins, color=color, title=title)
        fig = self._add_metadata(fig, source=source, period=period)
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=40, r=40, t=60, b=40),
            showlegend=color is not None,
        )
        return fig

    def scatter(
        self,
        x: str,
        y: str,
        color: str | None = None,
        title: str = "",
        size: str | None = None,
        hover_data: list[str] | None = None,
        source: str | None = None,
        period: str | None = None,
    ) -> go.Figure:
        """Cria gráfico de dispersão."""
        data = self._collect()
        fig = px.scatter(
            data,
            x=x,
            y=y,
            color=color,
            size=size,
            title=title,
            hover_data=hover_data or [],
        )
        fig = self._add_metadata(fig, source=source, period=period)
        fig.update_layout(template="plotly_dark", margin=dict(l=40, r=40, t=60, b=40))
        return fig

    def pie_chart(
        self,
        names: str,
        values: str,
        title: str = "",
        hole: float = 0.4,
        source: str | None = None,
        period: str | None = None,
    ) -> go.Figure:
        """Cria gráfico de pizza/donut."""
        data = self._collect()
        fig = px.pie(data, names=names, values=values, title=title, hole=hole)
        fig = self._add_metadata(fig, source=source, period=period)
        fig.update_layout(template="plotly_dark", margin=dict(l=40, r=40, t=60, b=40))
        return fig

    def line_chart(
        self,
        x: str,
        y: str,
        title: str = "",
        color: str | None = None,
        markers: bool = False,
        source: str | None = None,
        period: str | None = None,
    ) -> go.Figure:
        """Cria gráfico de linha."""
        data = self._collect()
        fig = px.line(data, x=x, y=y, color=color, title=title, markers=markers)
        fig = self._add_metadata(fig, source=source, period=period)
        fig.update_layout(template="plotly_dark", margin=dict(l=40, r=40, t=60, b=40))
        return fig

    def box_plot(
        self,
        y: str,
        x: str | None = None,
        title: str = "",
        color: str | None = None,
        source: str | None = None,
        period: str | None = None,
    ) -> go.Figure:
        """Cria box plot."""
        data = self._collect()
        fig = px.box(data, x=x, y=y, color=color, title=title)
        fig = self._add_metadata(fig, source=source, period=period)
        fig.update_layout(template="plotly_dark", margin=dict(l=40, r=40, t=60, b=40))
        return fig

    def heatmap(
        self,
        x: list[str] | None = None,
        y: list[str] | None = None,
        z: list[list[float]] | None = None,
        title: str = "",
        source: str | None = None,
        period: str | None = None,
    ) -> go.Figure:
        """Cria heatmap de correlação."""
        if z is None:
            # Calcula correlação se não fornecido
            df = self._collect()
            numeric_cols = [
                name for name, dtype in df.schema.items()
                if dtype in (pl.Int64, pl.Float64, pl.Int32, pl.Float32)
            ]
            if len(numeric_cols) < 2:
                return go.Figure()
            corr = df.select(numeric_cols).corr()
            z = corr.to_numpy().tolist()
            x = numeric_cols
            y = numeric_cols

        fig = go.Figure(data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            colorscale="RdBu",
            zmid=0,
        ))
        fig = self._add_metadata(fig, source=source, period=period)
        fig.update_layout(
            title=title,
            template="plotly_dark",
            margin=dict(l=40, r=40, t=60, b=40),
        )
        return fig

    def quality_dashboard(self, quality_metrics: dict[str, Any]) -> go.Figure:
        """Cria dashboard de qualidade de dados."""
        fig = make_subplots(
            rows=2,
            cols=2,
            specs=[
                [{"type": "indicator"}, {"type": "bar"}],
                [{"type": "pie", "colspan": 2}, None],
            ],
            subplot_titles=("Completude", "Valores Nulos por Coluna", "Status Geral"),
        )

        # Gauge de completude
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=quality_metrics.get("completeness_score", 0),
                title={"text": "Completude %"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#2ecc71"},
                    "steps": [
                        {"range": [0, 50], "color": "#e74c3c"},
                        {"range": [50, 80], "color": "#f39c12"},
                        {"range": [80, 100], "color": "#2ecc71"},
                    ],
                },
            ),
            row=1,
            col=1,
        )

        # Bar chart de nulos
        nulls = quality_metrics.get("null_percent", {})
        fig.add_trace(
            go.Bar(
                x=list(nulls.keys()),
                y=list(nulls.values()),
                marker_color="#e74c3c",
                name="Nulos %",
            ),
            row=1,
            col=2,
        )

        # Pie de status
        fig.add_trace(
            go.Pie(
                labels=["Válidos", "Nulos", "Duplicados"],
                values=[
                    quality_metrics.get("completeness_score", 100),
                    sum(nulls.values()) / max(len(nulls), 1),
                    quality_metrics.get("duplicate_rows", 0),
                ],
                marker=dict(colors=["#2ecc71", "#e74c3c", "#f39c12"]),
                hole=0.5,
            ),
            row=2,
            col=1,
        )

        fig.update_layout(
            title="Data Quality Dashboard",
            template="plotly_dark",
            showlegend=True,
            height=600,
        )
        return fig

    def hypothesis_summary(
        self,
        hypotheses: list[dict[str, Any]],
    ) -> go.Figure:
        """Cria sumário visual das hipóteses."""
        statuses: dict[str, int] = {}
        for h in hypotheses:
            status = h.get("status", "PENDENTE")
            statuses[status] = statuses.get(status, 0) + 1

        colors = {
            "CONFIRMADA": "#2ecc71",
            "REFUTADA": "#e74c3c",
            "PARCIALMENTE_CONFIRMADA": "#f39c12",
            "PENDENTE": "#95a5a6",
        }

        fig = go.Figure(data=[
            go.Pie(
                labels=list(statuses.keys()),
                values=list(statuses.values()),
                marker=dict(colors=[colors.get(s, "#95a5a6") for s in statuses.keys()]),
                hole=0.4,
            )
        ])
        fig.update_layout(
            title="Hipóteses por Status",
            template="plotly_dark",
            margin=dict(l=40, r=40, t=60, b=40),
        )
        return fig

    def kpi_cards(self, metrics: dict[str, float]) -> go.Figure:
        """Cria cards de KPI."""
        fig = make_subplots(
            rows=1,
            cols=len(metrics),
            specs=[[{"type": "indicator"}] * len(metrics)],
        )

        for i, (name, value) in enumerate(metrics.items(), 1):
            fig.add_trace(
                go.Indicator(
                    mode="number",
                    value=value,
                    title={"text": name},
                    number={"suffix": "%" if isinstance(value, (int, float)) and value < 100 else ""},
                ),
                row=1,
                col=i,
            )

        fig.update_layout(
            template="plotly_dark",
            showlegend=False,
            height=200,
        )
        return fig

    def distribution_comparison(
        self,
        column: str,
        segments: list[str] | None = None,
        title: str = "",
    ) -> go.Figure:
        """Compara distribuições por segmento."""
        data = self._collect()
        if not segments:
            return self.histogram(column, title=title or f"Distribuição de {column}")

        fig = px.histogram(
            data,
            x=column,
            color=segments[0] if segments else None,
            title=title or f"Distribuição de {column} por {segments[0]}",
            barmode="overlay",
            opacity=0.7,
        )
        fig.update_layout(template="plotly_dark")
        return fig

    def time_series_forecast(
        self,
        date_col: str,
        value_col: str,
        forecast_col: str | None = None,
        title: str = "",
    ) -> go.Figure:
        """Cria time series com forecast."""
        data = self._collect()
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=data[date_col],
            y=data[value_col],
            mode="lines",
            name="Real",
            line=dict(color="#2ecc71"),
        ))

        if forecast_col and forecast_col in data.columns:
            fig.add_trace(go.Scatter(
                x=data[date_col],
                y=data[forecast_col],
                mode="lines",
                name="Forecast",
                line=dict(color="#3498db", dash="dash"),
            ))

        fig.update_layout(
            title=title or f"Série Temporal: {value_col}",
            template="plotly_dark",
            xaxis_title=date_col,
            yaxis_title=value_col,
        )
        return fig

    def export_html(self, fig: go.Figure, filename: str) -> None:
        """Exporta figura como HTML."""
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(filename, include_plotlyjs="cdn")

    def export_image(self, fig: go.Figure, filename: str, width: int = 1920, height: int = 1080) -> None:
        """Exporta figura como imagem."""
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        fig.write_image(filename, width=width, height=height, scale=2)


class DashboardBuilder:
    """Constrói dashboards completos."""

    def __init__(
        self,
        df: pl.LazyFrame | pl.DataFrame,
        source: str | None = None,
        period: str | None = None,
    ) -> None:
        self.df = df
        self.charts: dict[str, go.Figure] = {}
        self._charts = ChartGenerator(df, source=source, period=period)

    def add_quality_dashboard(self, quality_metrics: dict[str, Any]) -> "DashboardBuilder":
        """Adiciona dashboard de qualidade."""
        self.charts["quality_dashboard"] = self._charts.quality_dashboard(quality_metrics)
        return self

    def add_kpis(self, metrics: dict[str, float]) -> "DashboardBuilder":
        """Adiciona cards de KPI."""
        self.charts["kpis"] = self._charts.kpi_cards(metrics)
        return self

    def add_hypothesis_summary(self, hypotheses: list[dict[str, Any]]) -> "DashboardBuilder":
        """Adiciona sumário de hipóteses."""
        self.charts["hypothesis_summary"] = self._charts.hypothesis_summary(hypotheses)
        return self

    def add_column_histogram(self, column: str) -> "DashboardBuilder":
        """Adiciona histograma de coluna."""
        self.charts[f"hist_{column}"] = self._charts.histogram(column)
        return self

    def add_correlation_heatmap(self) -> "DashboardBuilder":
        """Adiciona heatmap de correlação."""
        self.charts["correlation"] = self._charts.heatmap()
        return self

    def build(self, title: str = "Analytics Dashboard") -> go.Figure:
        """Constrói dashboard completo com múltiplos painéis."""
        n_charts = len(self.charts)
        if n_charts == 0:
            return go.Figure()

        cols = min(2, n_charts)
        rows = (n_charts + cols - 1) // cols

        fig = make_subplots(
            rows=rows,
            cols=cols,
            subplot_titles=list(self.charts.keys()),
        )

        for i, (name, chart) in enumerate(self.charts.items(), 1):
            row = (i - 1) // cols + 1
            col = (i - 1) % cols + 1

            for trace in chart.data:
                fig.add_trace(trace, row=row, col=col)

        fig.update_layout(
            title_text=title,
            template="plotly_dark",
            showlegend=False,
            height=300 * rows,
        )
        return fig

    def export_all(self, output_dir: str) -> dict[str, str]:
        """Exporta todos os gráficos como HTML."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        exported = {}
        for name, fig in self.charts.items():
            filename = output_path / f"{name}.html"
            fig.write_html(filename, include_plotlyjs="cdn")
            exported[name] = str(filename)

        # Dashboard completo
        dashboard = self.build()
        dashboard.write_html(output_path / "dashboard.html", include_plotlyjs="cdn")
        exported["dashboard"] = str(output_path / "dashboard.html")

        return exported