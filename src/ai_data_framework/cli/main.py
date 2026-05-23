"""CLI principal do AI Data Framework."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ai_data_framework.pipeline.orchestrator import AnalyticsPipeline
from ai_data_framework.core.entities import HypothesisStatus

console = Console()


def main() -> None:
    """Entry point principal."""
    console.print(Panel.fit(
        "[bold cyan]AI Data Framework[/bold cyan]\n"
        "Framework analítico orientado a hipóteses",
        border_style="cyan",
    ))

    if len(sys.argv) < 2:
        _show_help()
        return

    command = sys.argv[1]

    if command == "run":
        _run_pipeline()
    elif command == "profile":
        _run_profile()
    elif command == "validate":
        _run_validate()
    elif command == "dashboard":
        _run_dashboard()
    elif command == "hypotheses":
        _run_hypotheses()
    elif command == "insights":
        _run_insights()
    else:
        console.print(f"[red]Comando desconhecido: {command}[/red]")
        _show_help()


def _show_help() -> None:
    """Mostra ajuda."""
    console.print("\n[bold]Comandos:[/bold]")
    console.print("  run        - Executa pipeline completo")
    console.print("  profile    - Apenas profiling de dados")
    console.print("  validate   - Valida hipóteses")
    console.print("  dashboard  - Gera dashboard HTML")
    console.print("  hypotheses - Lista hipóteses geradas")
    console.print("  insights   - Mostra insights gerados")
    console.print("\n[bold]Uso:[/bold]")
    console.print("  ai-data run <source> [--problem=<statement>] [--llm=<provider>] [--output=<dir>]")
    console.print("  ai-data profile <source>")
    console.print("  ai-data validate <source>")
    console.print("  ai-data dashboard <source> [--output=<dir>]")
    console.print("\n[bold]Opções LLM:[/bold]")
    console.print("  --llm=minimax   (padrão)")
    console.print("  --llm=anthropic")
    console.print("  --llm=openai")
    console.print("  --llm=litellm")
    console.print("\n[bold]Exemplos:[/bold]")
    console.print("  ai-data run dados.csv --problem='Queda nas vendas'")
    console.print("  ai-data run dados.csv --llm=openai --problem='Análise de churn'")
    console.print("  ai-data profile dados.csv")
    console.print("  ai-data dashboard dados.csv --output=./dashboards")


def _parse_args(min_args: int, usage: str) -> bool:
    """Valida argumentos mínimos."""
    if len(sys.argv) < min_args:
        console.print(f"[red]Uso: {usage}[/red]")
        return False
    return True


def _run_pipeline() -> None:
    """Executa pipeline completo."""
    if not _parse_args(3, "ai-data run <source> [--problem=<statement>]"):
        return

    source = sys.argv[2]
    problem = None
    output_dir = None
    llm_provider = "minimax"

    for arg in sys.argv[3:]:
        if arg.startswith("--problem="):
            problem = arg.split("=", 1)[1]
        elif arg.startswith("--output="):
            output_dir = arg.split("=", 1)[1]
        elif arg.startswith("--llm="):
            llm_provider = arg.split("=", 1)[1]

    console.print(f"[cyan]Carregando dados de: {source}[/cyan]")
    console.print(f"[dim]LLM: {llm_provider}[/dim]")

    pipeline = AnalyticsPipeline(llm_provider=llm_provider)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            t1 = progress.add_task("[cyan]Carregando dados...", total=None)
            context = pipeline.load_data(source)
            progress.update(t1, description=f"[green]✓ Dados carregados: {context.shape[0]} linhas")

            t2 = progress.add_task("[cyan]Analisando estrutura...", total=None)
            profiling = pipeline.profile_data()
            progress.update(t2, description=f"[green]✓ Completude: {profiling['quality_metrics']['completeness_score']:.1f}%")

            t3 = progress.add_task("[cyan]Gerando hipóteses...", total=None)
            hypotheses = pipeline.generate_hypotheses(problem)
            progress.update(t3, description=f"[green]✓ {len(hypotheses)} hipóteses geradas")

            t4 = progress.add_task("[cyan]Validando hipóteses...", total=None)
            validated = pipeline.validate_hypotheses()
            progress.update(t4, description=f"[green]✓ Hipóteses validadas")

            t5 = progress.add_task("[cyan]Gerando insights...", total=None)
            insights = pipeline.generate_insights()
            progress.update(t5, description=f"[green]✓ {len(insights)} insights gerados")

            if output_dir:
                t6 = progress.add_task("[cyan]Exportando dashboards...", total=None)
                exported = pipeline.create_dashboard(output_dir)
                progress.update(t6, description=f"[green]✓ Dashboards em {output_dir}")

        console.print("\n[bold green]✓ Pipeline concluído![/bold green]\n")
        _show_summary(context)

        if output_dir:
            console.print(f"\n[bold]Dashboards exportados para:[/bold] {output_dir}")
            console.print("  - dashboard.html (visão geral)")
            console.print("  - quality_dashboard.html (qualidade)")
            console.print("  - hypothesis_summary.html (sumário)")

    except FileNotFoundError:
        console.print(f"[bold red]✗ Arquivo não encontrado: {source}[/bold red]")
    except Exception as e:
        console.print(f"[bold red]✗ Erro: {e}[/bold red]")


def _run_profile() -> None:
    """Executa apenas profiling."""
    if not _parse_args(3, "ai-data profile <source>"):
        return

    source = sys.argv[2]
    pipeline = AnalyticsPipeline()

    try:
        pipeline.load_data(source)
        results = pipeline.profile_data()

        qm = results["quality_metrics"]

        console.print("\n[bold]Quality Report[/bold]\n")

        # Overview table
        table = Table(title="Overview", show_header=True)
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")
        table.add_row("Total Rows", f"{qm['total_rows']:,}")
        table.add_row("Total Columns", str(qm['total_columns']))
        table.add_row("Completeness", f"{qm['completeness_score']:.1f}%")
        table.add_row("Duplicate Rows", str(qm['duplicate_rows']))
        console.print(table)

        # Data types
        if qm.get("data_types"):
            dt_table = Table(title="Data Types", show_header=True)
            dt_table.add_column("Column", style="cyan")
            dt_table.add_column("Type", style="yellow")
            for col, dtype in qm["data_types"].items():
                dt_table.add_row(col, dtype)
            console.print("\n")
            console.print(dt_table)

        # Null percentages
        nulls = qm.get("null_percent", {})
        if nulls:
            console.print("\n[bold]Null Percentages[/bold]\n")
            for col, pct in sorted(nulls.items(), key=lambda x: x[1], reverse=True):
                color = "red" if pct > 20 else "yellow" if pct > 5 else "green"
                console.print(f"  {col}: [{color}]{pct:.1f}%[/{color}]")

        # Suggestions
        if results.get("suggestions"):
            console.print("\n[bold]Suggestions[/bold]\n")
            for s in results["suggestions"]:
                console.print(f"  • [{s.get('potential_impact', 'Médio').lower()}] {s.get('description', '')}")

    except FileNotFoundError:
        console.print(f"[bold red]✗ Arquivo não encontrado: {source}[/bold red]")
    except Exception as e:
        console.print(f"[bold red]✗ Erro: {e}[/bold red]")


def _run_validate() -> None:
    """Valida hipóteses existentes."""
    if not _parse_args(3, "ai-data validate <source>"):
        return

    source = sys.argv[2]
    pipeline = AnalyticsPipeline()

    try:
        pipeline.load_data(source)
        pipeline.profile_data()
        hypotheses = pipeline.generate_hypotheses()
        validated = pipeline.validate_hypotheses()

        console.print("\n[bold]Validation Results[/bold]\n")

        table = Table(show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Status", style="bold")
        table.add_column("Confidence")

        for h in validated:
            status_color = {
                HypothesisStatus.CONFIRMADA: "green",
                HypothesisStatus.REFUTADA: "red",
                HypothesisStatus.PARCIALMENTE_CONFIRMADA: "yellow",
                HypothesisStatus.PENDENTE: "dim",
            }.get(h.status, "white")

            table.add_row(
                h.id,
                h.title[:35] + "..." if len(h.title) > 35 else h.title,
                f"[{status_color}]{h.status.value}[/{status_color}]",
                f"{h.confidence:.0%}",
            )

        console.print(table)

        # Summary
        confirmed = len([h for h in validated if h.status == HypothesisStatus.CONFIRMADA])
        refuted = len([h for h in validated if h.status == HypothesisStatus.REFUTADA])
        partial = len([h for h in validated if h.status == HypothesisStatus.PARCIALMENTE_CONFIRMADA])

        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  [green]✓ Confirmadas: {confirmed}[/green]")
        console.print(f"  [red]✗ Refutadas: {refuted}[/red]")
        console.print(f"  [yellow]~ Parciais: {partial}[/yellow]")

    except FileNotFoundError:
        console.print(f"[bold red]✗ Arquivo não encontrado: {source}[/bold red]")
    except Exception as e:
        console.print(f"[bold red]✗ Erro: {e}[/bold red]")


def _run_dashboard() -> None:
    """Gera dashboard HTML."""
    if not _parse_args(3, "ai-data dashboard <source> [--output=<dir>]"):
        return

    source = sys.argv[2]
    output_dir = "dashboards"

    for arg in sys.argv[3:]:
        if arg.startswith("--output="):
            output_dir = arg.split("=", 1)[1]

    pipeline = AnalyticsPipeline()

    try:
        pipeline.load_data(source)
        pipeline.profile_data()
        pipeline.generate_hypotheses()
        pipeline.validate_hypotheses()
        pipeline.generate_insights()

        exported = pipeline.create_dashboard(output_dir)

        console.print(f"\n[bold green]✓ Dashboard exportado![/bold green]\n")
        console.print(f"[bold]Arquivos gerados em:[/bold] {output_dir}")
        for name, path in exported.items():
            console.print(f"  • {name}: {path}")

    except FileNotFoundError:
        console.print(f"[bold red]✗ Arquivo não encontrado: {source}[/bold red]")
    except Exception as e:
        console.print(f"[bold red]✗ Erro: {e}[/bold red]")


def _run_hypotheses() -> None:
    """Mostra hipóteses geradas."""
    console.print("[yellow]Funcionalidade em desenvolvimento[/yellow]")
    console.print("Use: ai-data run <source> para executar pipeline completo")


def _run_insights() -> None:
    """Mostra insights gerados."""
    console.print("[yellow]Funcionalidade em desenvolvimento[/yellow]")
    console.print("Use: ai-data run <source> para executar pipeline completo")


def _show_summary(context: Any) -> None:
    """Mostra sumário do pipeline."""
    if context.hypotheses:
        table = Table(title="Hipóteses", show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Título", style="white")
        table.add_column("Status", style="bold")
        table.add_column("Confiança")

        for h in context.hypotheses:
            status_color = {
                HypothesisStatus.CONFIRMADA: "green",
                HypothesisStatus.REFUTADA: "red",
                HypothesisStatus.PARCIALMENTE_CONFIRMADA: "yellow",
                HypothesisStatus.PENDENTE: "dim",
            }.get(h.status, "white")

            table.add_row(
                h.id,
                h.title[:40],
                f"[{status_color}]{h.status.value}[/{status_color}]",
                f"{h.confidence:.0%}",
            )

        console.print(table)

    if context.insights:
        console.print(f"\n[bold]Insights gerados: {len(context.insights)}[/bold]")
        for i, insight in enumerate(context.insights, 1):
            console.print(f"\n[bold cyan]{i}. {insight.title}[/bold cyan]")
            console.print(f"   {insight.description[:100]}...")
            console.print(f"   Impacto: {insight.business_impact} | Confiança: {insight.confidence:.0%}")

    # Stats
    console.print("\n[bold]Estatísticas:[/bold]")
    console.print(f"  Total Hipóteses: {len(context.hypotheses)}")
    console.print(f"  Confirmadas: {len(context.get_confirmed_hypotheses())}")
    console.print(f"  Refutadas: {len(context.get_refuted_hypotheses())}")


if __name__ == "__main__":
    main()