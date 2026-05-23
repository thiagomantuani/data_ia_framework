"""FastAPI web server for AI Data Framework."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from ai_data_framework.pipeline.orchestrator import AnalyticsPipeline
import polars as pl

app = FastAPI(title="AI Data Framework", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
BASE_DIR = Path(__file__).parent.parent
web_dir = BASE_DIR / "web"
index_path = web_dir / "index.html"

# Global pipeline log
_pipeline_log: list[dict] = []


def _log(step: str, message: str, status: str = "info"):
    entry = {"step": step, "message": message, "status": status}
    _pipeline_log.append(entry)
    print(f"[{step.upper()}] {message}", flush=True)


def _build_charts(pipeline: AnalyticsPipeline) -> dict[str, Any]:
    """Build chart data for frontend visualization."""
    charts = {}
    try:
        from ai_data_framework.visualization.charts import ChartGenerator

        df = pipeline.context.dataset.data
        if hasattr(df, 'collect'):
            df = df.collect()

        chart_gen = ChartGenerator(df)

        # 1. Quality bar chart (nulls per column)
        nulls = pipeline.context.metadata.get("profiling", {}).get("quality_metrics", {}).get("null_percent", {})
        if nulls:
            charts["nulls_bar"] = {
                "type": "bar",
                "title": "Valores Nulos por Coluna",
                "data": {
                    "labels": list(nulls.keys()),
                    "values": [round(v, 1) for v in nulls.values()],
                },
                "colors": ["#e74c3c" if v > 20 else "#06b6d4" for v in nulls.values()],
            }

        # 2. Completeness gauge
        completeness = pipeline.context.metadata.get("profiling", {}).get("quality_metrics", {}).get("completeness_score", 0)
        charts["completeness"] = {
            "type": "gauge",
            "title": "Completude do Dataset",
            "value": round(completeness, 1),
            "color": "#22c55e" if completeness > 80 else "#eab308" if completeness > 50 else "#ef4444",
        }

        # 3. Hypothesis status pie
        hypotheses = pipeline.context.hypotheses
        status_counts = {"CONFIRMADA": 0, "REFUTADA": 0, "PARCIALMENTE_CONFIRMADA": 0, "PENDENTE": 0}
        for h in hypotheses:
            status_counts[h.status.value] = status_counts.get(h.status.value, 0) + 1

        charts["hypothesis_status"] = {
            "type": "pie",
            "title": "Status das Hipóteses",
            "labels": list(status_counts.keys()),
            "values": list(status_counts.values()),
            "colors": ["#22c55e", "#ef4444", "#eab308", "#71717a"],
        }

        # 4. Column types distribution
        col_details = []
        try:
            df_schema = df.schema
            type_counts = {"numeric": 0, "string": 0, "date": 0, "boolean": 0}
            for col_name, dtype in df_schema.items():
                dtype_str = str(dtype).lower()
                if "int" in dtype_str or "float" in dtype_str:
                    type_counts["numeric"] += 1
                elif "bool" in dtype_str:
                    type_counts["boolean"] += 1
                elif "date" in dtype_str or "time" in dtype_str:
                    type_counts["date"] += 1
                else:
                    type_counts["string"] += 1
            charts["column_types"] = {
                "type": "pie",
                "title": "Tipos de Colunas",
                "labels": list(type_counts.keys()),
                "values": list(type_counts.values()),
                "colors": ["#06b6d4", "#a855f7", "#eab308", "#ec4899"],
            }
        except Exception:
            pass

        # 5. Numeric column histograms (top 4)
        numeric_cols = []
        try:
            numeric_cols = [
                c for c in df.columns
                if df[c].dtype in {pl.Int64, pl.Int32, pl.Float64, pl.Float32}
            ]
        except Exception:
            numeric_cols = []

        for col in numeric_cols[:4]:
            try:
                col_data = df[col].drop_nulls()
                if len(col_data) > 0:
                    # Create bins for histogram
                    min_val = float(col_data.min())
                    max_val = float(col_data.max())
                    bins = 20
                    step = (max_val - min_val) / bins if max_val > min_val else 1
                    hist_vals = [0] * bins
                    for v in col_data:
                        idx = min(int((float(v) - min_val) / step), bins - 1)
                        hist_vals[idx] += 1

                    charts[f"hist_{col}"] = {
                        "type": "histogram",
                        "title": f"Distribuição: {col}",
                        "data": {
                            "x": [round(min_val + i * step, 2) for i in range(bins)],
                            "y": hist_vals,
                        },
                        "x_label": col,
                        "y_label": "Frequência",
                    }
            except Exception:
                continue

        # 6. Top correlations heatmap
        correlations = pipeline.context.metadata.get("profiling", {}).get("correlations", {})
        if correlations:
            strong_corrs = {k: v for k, v in correlations.items() if abs(v) > 0.5}
            if strong_corrs:
                labels = []
                values = []
                for pair, corr in list(strong_corrs.items())[:10]:
                    col1, col2 = pair.split("__")
                    labels.append(f"{col1} ↔ {col2}")
                    values.append(round(corr, 3))

                charts["correlations_bar"] = {
                    "type": "bar",
                    "title": "Correlações Fortes (|r| > 0.5)",
                    "data": {"labels": labels, "values": values},
                    "colors": ["#22c55e" if v > 0 else "#ef4444" for v in values],
                }

    except Exception as e:
        _log("charts", f"Erro gerando gráficos: {str(e)}", "error")

    return charts


async def run_pipeline_stream(source: str, problem: str | None, llm_provider: str, filename: str = "dataset"):
    """Executa o pipeline com streaming de logs."""
    global _pipeline_log
    _pipeline_log.clear()

    try:
        _log("init", f"Iniciando pipeline com {filename}")
        _log("init", f"Problema: {problem or 'Análise geral'}")
        _log("init", f"LLM: {llm_provider}")

        pipeline = AnalyticsPipeline(llm_provider=llm_provider)

        # Load data
        _log("load", "Carregando arquivo...")
        context = pipeline.load_data(source)
        _log("load", f"Dados carregados: {context.shape[0]} linhas, {context.shape[1]} colunas")

        # Profile data
        _log("structure", "Analisando estrutura dos dados...")
        profiling = pipeline.profile_data()
        _log("structure", "Estrutura analisada com sucesso")

        # Generate hypotheses
        _log("hypotheses", "Gerando hipóteses (mínimo 5)...")
        hypotheses = pipeline.generate_hypotheses(problem)
        _log("hypotheses", f"{len(hypotheses)} hipóteses geradas")

        # Validate hypotheses
        _log("validate", "Validando hipóteses...")
        validated = pipeline.validate_hypotheses()
        confirmed = [h for h in validated if h.status.value == "CONFIRMADA"]
        refuted = [h for h in validated if h.status.value == "REFUTADA"]
        partial = [h for h in validated if h.status.value == "PARCIALMENTE_CONFIRMADA"]
        _log("validate", f"Validação: {len(confirmed)} confirmadas, {len(refuted)} refutadas, {len(partial)} parciais")

        # Generate insights
        _log("insights", "Gerando insights...")
        insights = pipeline.generate_insights()
        _log("insights", f"{len(insights)} insights produzidos")

        # Build charts
        _log("charts", "Gerando visualizações...")
        charts = _build_charts(pipeline)
        _log("charts", f"{len(charts)} gráficos produzidos")

        quality = profiling.get("quality_metrics", {})

        result = {
            "status": "success",
            "dataset": {
                "name": filename,
                "rows": context.shape[0],
                "columns": context.shape[1],
                "sample": _get_sample(pipeline.context.dataset),
                "columns_detail": _get_columns_detail(pipeline.context.dataset),
                "quality": {
                    "completeness": quality.get("completeness_score", 0),
                    "duplicates": quality.get("duplicate_rows", 0),
                    "nulls": quality.get("null_percent", {}),
                },
            },
            "hypotheses": [h.to_dict() for h in validated],
            "insights": [i.to_dict() for i in insights],
            "charts": charts,
        }

        _log("done", "Pipeline finalizado com sucesso!", "success")
        return result

    except Exception as e:
        _log("error", f"Erro: {str(e)}", "error")
        raise


def _get_sample(ds) -> list[dict]:
    """Get sample rows from Dataset (handles LazyFrame)."""
    try:
        if hasattr(ds, 'data'):
            df = ds.data.collect() if hasattr(ds.data, 'collect') else ds.data
        else:
            df = ds
        sample = df.head(10)
        return sample.to_dict(orient="records")
    except Exception:
        return []


def _get_columns_detail(ds) -> list[dict]:
    """Get column details from Dataset (handles LazyFrame)."""
    details = []
    try:
        if hasattr(ds, 'data'):
            df = ds.data.collect() if hasattr(ds.data, 'collect') else ds.data
            col_names = ds.schema.names() if hasattr(ds, 'schema') else df.columns
        else:
            df = ds
            col_names = df.columns
    except Exception:
        return []

    for col_name in col_names:
        try:
            col_data = df[col_name]
            dtype = str(col_data.dtype)
            if "int" in dtype or "float" in dtype:
                col_type = "numeric"
            elif "datetime" in dtype or "date" in dtype:
                col_type = "date"
            elif "bool" in dtype:
                col_type = "boolean"
            else:
                col_type = "string"

            null_pct = round(col_data.is_null().mean() * 100, 1) if len(col_data) > 0 else 0

            stats = {}
            if col_type == "numeric":
                try:
                    stats = {
                        "mean": float(col_data.mean()),
                        "median": float(col_data.median()),
                        "min": float(col_data.min()),
                        "max": float(col_data.max()),
                        "std": float(col_data.std()),
                    }
                except Exception:
                    pass

            example_val = ""
            try:
                not_null = col_data.drop_nulls()
                if len(not_null) > 0:
                    example_val = str(not_null[0])[:50]
            except Exception:
                pass

            details.append({
                "name": col_name,
                "type": col_type,
                "nulls": null_pct,
                "unique": int(col_data.n_unique()) if len(col_data) > 0 else 0,
                "example": example_val,
                "stats": stats,
            })
        except Exception:
            continue
    return details


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """Serve main dashboard HTML."""
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(content="<h1>index.html not found</h1>", status_code=404)


@app.get("/api/log")
async def get_log() -> JSONResponse:
    """Retorna logs do pipeline."""
    return JSONResponse(content={"logs": _pipeline_log})


@app.post("/api/run")
async def run(
    file: UploadFile,
    problem: str = "Análise geral",
    llm: str = "minimax",
) -> JSONResponse:
    """Run pipeline on uploaded file."""
    suffix = Path(file.filename or "tmp").suffix.lower()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await run_pipeline_stream(tmp_path, problem, llm, filename=file.filename or "dataset")
        return JSONResponse(content=result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.post("/api/profile")
async def profile(file: UploadFile) -> JSONResponse:
    """Profile uploaded file."""
    suffix = Path(file.filename or "tmp").suffix.lower()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        pipeline = AnalyticsPipeline(llm_provider="minimax")
        pipeline.load_data(tmp_path)
        profiling = pipeline.profile_data()
        return JSONResponse(content={"status": "success", "profiling": profiling})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)