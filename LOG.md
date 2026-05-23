# AI Data Framework - LOG de Desenvolvimento

## Histórico

### 2025-05-22 - v0.1.0 (alpha)

#### O que foi feito:

1. **Estrutura base do projeto**
   - Setup com `uv` (Python 3.12)
   - `pyproject.toml` com dependências: pandas, polars, pydantic, plotly, rich, httpx, etc.
   - CLI funcional com `ai-data` entry point

2. **Módulos implementados:**
   - `core/entities.py` — Dataset, Hypothesis, Insight, PipelineContext
   - `ingestion/loaders.py` — CSV, Parquet, Excel, SQL loaders
   - `profiling/analyzer.py` — DataProfiler com métricas de qualidade
   - `hypothesis/generator.py` — HypothesisGenerator (rule-based fallback)
   - `validation/validator.py` — HypothesisValidator com validação quantitativa
   - `visualization/charts.py` — ChartGenerator com Plotly
   - `llm/client.py` — MiniMaxClient, AnthropicClient, OpenAIClient, LiteLLMClient
   - `pipeline/orchestrator.py` — AnalyticsPipeline completo
   - `cli/main.py` — Interface de linha de comando

3. **Integração MiniMax:**
   - MiniMaxClient com API `https://api.minimax.chat/v1/text/chatcompletion_v2`
   - Modelo: `MiniMax-M2.7`
   - Provider padrão do LLMClient configurado para `minimax`
   - Suporte a `--llm=minimax|anthropic|openai|litellm`

4. **CLI comandos:**
   - `ai-data run <source> [--problem=<stmt>] [--llm=<provider>] [--output=<dir>]`
   - `ai-data profile <source>`
   - `ai-data validate <source>`
   - `ai-data dashboard <source> [--output=<dir>]`

5. **Testes:**
   - `tests/test_core.py`
   - `tests/test_ingestion.py`
   - `tests/test_profiling.py`
   - `tests/test_hypothesis.py`
   - `tests/test_visualization.py`

6. **Documentação:**
   - `README.md`
   - `Agents.md`
   - `Arquiteture_guidelines.md`
   - `Estrutura.md`
   - `Metodologia.md`
   - `.env.example` (variáveis MINIMAX_API_KEY, MINIMAX_GROUP_ID)

---

#### Bugs corrigidos:
- `[bold cyan]AI Data Framework[/cyan]` → `[bold cyan]AI Data Framework[/bold cyan]` (Rich markup)

---

#### O que falta fazer:

**Alta prioridade:**
- [ ] Testar MiniMaxClient com credenciais reais
- [ ] Adicionar suporte a `--problem` no `ai-data profile`
- [ ] Criar dataset de exemplo para demonstração (sample_sales.csv)

**Média prioridade:**
- [ ] `ai-data hypotheses` — listar hipóteses do último run
- [ ] `ai-data insights` — listar insights do último run
- [ ] Persistir contexto entre execuções (JSON em ~/.ai-data/)
- [ ] Dashboard interativo com filtro por hipótese

**Baixa prioridade:**
- [ ] Exportar resultados em CSV/JSON
- [ ] Suporte a streaming do LLM
- [ ] Cache de profiling para arquivos grandes
- [ ] Integração com dbt / dbt Core

---

#### Configuração para uso:

```bash
# Variáveis de ambiente
export MINIMAX_API_KEY="sua_chave_aqui"
export MINIMAX_GROUP_ID="seu_group_id_aqui"

# Instalar e rodar
cd /home/hermes/repositorio/data_ia_framework
uv sync
ai-data run dados.csv --problem="Queda no faturamento"
```

---

#### Roadmap:
- v0.1.1 — Fix `hypotheses` e `insights` commands
- v0.2.0 — Persistência de contexto + dashboard interativo
- v0.3.0 — Integração dbt + suporte a streaming