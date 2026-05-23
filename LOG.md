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

### 2025-05-22 - v0.1.1 (alpha) — Correções e gráficos

#### Bugs/Issues corrigidos:
- `[bold cyan]AI Data Framework[/bold cyan]` (Rich markup)
- Validação de hipóteses não estava sendo executada → reescrito `validator.py` com 8 métodos de validação
- Gráficos não eram gerados → adicionado `_build_charts()` no `server.py` + renderer SVG no frontend
- `profiling/analyzer.py` não computava outliers%, skewness, high_variance → corrigido
- HTML estrutural malformed no subsection de charts → corrigido
- `web.server` não estava no PYTHONPATH correto → corrigido comando de start

#### Novos recursos:
- **Hipóteses**: gerador agora tenta extrair mínimo 5 hipóteses do perfil dos dados
- **Validação melhorada**: 8 tipos de validação (missing, correlação, variância, outliers, duplicados, completude, distribuição, temporal)
- **Gráficos SVG nativos**: bar chart, pie chart, gauge, histogram — sem dependência de Plotly no frontend
- **Charts renderizados no backend**: `_build_charts()` gera dados para o frontend (bar, pie, gauge, histogram, correlações)

#### O que falta fazer:

**Alta prioridade:**
- [ ] Testar MiniMaxClient com credenciais reais
- [ ] Testar pipeline completo com arquivo CSV de exemplo
- [ ] Adicionar suporte a `--problem` no `ai-data profile`

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

---

## Tarefas Kanban - data_ia_framework

### [BUG] Navegação de sub-abas na aba "Estrutura" não funciona
- **Projeto:** data_ia_framework
- **Tipo:** Bug
- **Descrição:** Na aba "Estrutura" do dashboard web, as sub-abas (Colunas, Gráficos, etc.) não navegam quando clicadas. A navegação por abas em `index.html` precisa ser corrigida.
- **Arquivo:** web/index.html
- **Assignee:** desenvolvedor

### [MELHORIA] Gerar hipóteses de negócio (não técnicas/estatísticas)
- **Projeto:** data_ia_framework
- **Tipo:** Melhoria
- **Descrição:** As hipóteses geradas atualmente são muito técnicas/estatísticas (ex: "Alta variabilidade em revenue", "Correlação entre colunas"). Precisa mudar o gerador para produzir hipóteses voltadas a negócio. Exemplos: "Adicionar item complementar ao pedido aumenta ticket médio em X%", "Clientes insatisfeitos churnam mais", "Região X tem receita abaixo da média".
- **Arquivo:** src/hypothesis/generator.py
- **Assignee:** desenvolvedor

### [MELHORIA] Gráficos profissionais para hypotheses (bar, pie, heatmap)
- **Projeto:** data_ia_framework
- **Tipo:** Melhoria
- **Descrição:** As hipóteses validadas precisam ter gráficos profissionais dedicados: bar charts de distribuição, pie charts de status, heatmaps de correlação. Atualmente não há gráficos na seção de hipóteses.
- **Arquivo:** src/visualization/charts.py
- **Assignee:** desenvolvedor

### [BUG] Charts do backend não aparecem no frontend (estrutura/gráficos)
- **Projeto:** data_ia_framework
- **Tipo:** Bug
- **Descrição:** Corrigir renderização de gráficos no frontend - os charts são gerados no backend (`_build_charts`) mas o frontend não os exibe corretamente na seção "Gráficos" da aba Estrutura.
- **Arquivo:** web/index.html, web/server.py
- **Assignee:** desenvolvedor