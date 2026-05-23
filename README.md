# AI Data Framework

Framework analítico orientado a hipóteses para análise de dados com Inteligência Artificial.

## Objetivo

Transformar datasets brutos em:
- hipóteses de negócio
- validações quantitativas
- insights executivos
- recomendações acionáveis

## Arquitetura

```
LOAD_DATA → PROFILE_STRUCTURE → DATA_QUALITY_ANALYSIS → GENERATE_HYPOTHESES
    ↓
PRIORITIZE_HYPOTHESES → VALIDATE_HYPOTHESES → GENERATE_INSIGHTS
    ↓
BUILD_DASHBOARD → EXPORT_RESULTS
```

## Instalação

```bash
pip install -e .
```

## Uso

```bash
ai-data --help
```

## Estrutura do Projeto

- `core/` — Entidades de domínio (Hypothesis, Dataset, Insight)
- `ingestion/` — Carregamento de dados (CSV, Parquet, SQL, Excel)
- `profiling/` — Análise de estrutura e qualidade
- `hypothesis/` — Geração de hipóteses de negócio
- `validation/` — Validação quantitativa de hipóteses
- `visualization/` — Gráficos e dashboards
- `llm/` — Integração com LLMs
- `pipeline/` — Orquestração do fluxo analítico
- `cli/` — Interface de linha de comando

## Filosofia

- Toda recomendação deve ser rastreável, validada e reproduzível
- A IA nunca gera conclusões sem evidência numérica
- Tipagem estrita com mypy + pydantic