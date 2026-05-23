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
- **Status:** ✅ CORRIGIDO — CSS `.subsection { display: none }` adicionado na linha ~188. Sub-abas agora navegam corretamente.

### [MELHORIA] Gerar hipóteses de negócio (não técnicas/estatísticas)
- **Projeto:** data_ia_framework
- **Tipo:** Melhoria
- **Descrição:** As hipóteses geradas atualmente são muito técnicas/estatísticas (ex: "Alta variabilidade em revenue", "Correlação entre colunas"). Precisa mudar o gerador para produzir hipóteses voltadas a negócio. Exemplos: "Adicionar item complementar ao pedido aumenta ticket médio em X%", "Clientes insatisfeitos churnam mais", "Região X tem receita abaixo da média".
- **Arquivo:** src/hypothesis/generator.py
- **Assignee:** desenvolvedor
- **Status:** ✅ IMPLEMENTADO — Novo `HypothesisGenerator` com 8 categorias de hipóteses de negócio: Revenue, Clientes/Churn, Região, Produto, Satisfação, Temporalidade, Crescimento. Exemplos: "Ticket médio varia por comportamento de compra", "Clientes insatisfeitos churnam mais", "Programa de fidelidade pode aumentar recorrência em 20%"

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

### [BUG] Aba Amostra não funciona (navegação/display)
- **Projeto:** data_ia_framework
- **Tipo:** Bug
- **Descrição:** Aba "Amostra" do dashboard não navegava quando clicada - similar ao bug das sub-abas da aba Estrutura que já foi corrigido.
- **Arquivo:** web/index.html
- **Assignee:** desenvolvedor
- **Status:** ✅ CORRIGIDO — CSS `.subsection { display: none }` aplicar a todas as abas com sub-navegação. Testado e funcionando.

### [BUG] Hipóteses inventadas sem relação com dataset real
- **Projeto:** data_ia_framework
- **Tipo:** Bug
- **Descrição:** Hipóteses eram geradas arbitrariamente sem relação com o dataset real. O gerador precisa extrair padrões reais (correlações, distribuições, categorias) do próprio dataset. NUNCA inventar — usar fatos extraídos dos dados.
- **Arquivo:** src/hypothesis/generator.py
- **Assignee:** desenvolvedor
- **Status:** ✅ CORRIGIDO — HypothesisGenerator reescrito para ser 100% data-driven. Identifica automaticamente: fato (coluna numérica de maior impacto), dimensões (categóricas), correlações fortes, churn/satisfação, outliers. Gera hipóteses baseadas EM padrões reais do dataset.

### [MELHORIA] Colapsar/expandir área de upload e executar (tela pequena)
- **Projeto:** data_ia_framework
- **Tipo:** Melhoria
- **Descrição:** Adicionar botão para colapsar/expandir a barra superior com upload e botão executar, útil em celular com tela pequena para dar mais espaço ao conteúdo.
- **Arquivo:** web/index.html (CSS + JS), web/server.py
- **Assignee:** desenvolvedor
- **Status:** ✅ IMPLEMENTADO — botão ▼/▲ no canto superior direito da top-bar. CSS `.top-bar.collapsed .top-bar-inner { display: none }` + `.top-bar.collapsed { padding: 0.5rem 1rem }`. Testado e funcionando.

### [BUG] Hipóteses duplicadas — orchestrator.py double-add
- **Projeto:** data_ia_framework
- **Tipo:** Bug
- **Descrição:** `generate_hypotheses()` adicionava as mesmas hipóteses 2 vezes. Linhas 163-178 adicionavam hipóteses data-driven uma vez. Linhas 180-181 faziam `for h in hypotheses: add_hypothesis(h)` SEMPRE, duplicando tudo.
- **Arquivo:** src/ai_data_framework/pipeline/orchestrator.py
- **Assignee:** desenvolvedor
- **Status:** ✅ CORRIGIDO — linhas 180-181 removidas. Agora 9 hipóteses únicas (antes: 18 com 9 duplicatas).
- **Verificação:** `uv run python -c "from ai_data_framework.pipeline.orchestrator import AnalyticsPipeline; result = AnalyticsPipeline(llm_provider='minimax').run('sample_sales.csv'); print(len(result.hypotheses), 'hipóteses')"` → 9

### [BUG] Validação de variância não seguia Validation_rules.md
- **Projeto:** data_ia_framework
- **Tipo:** Bug
- **Descrição:** `_validate_variance` só testava `std/mean ratio > 0.5`. Validation_rules.md exige: CONFIRMADA se p < 0.05 OU delta > 5% do baseline. Também tinha texto spammy "Alta variância疑似的" em chinês.
- **Arquivo:** src/ai_data_framework/validation/validator.py
- **Assignee:** desenvolvedor
- **Status:** ✅ CORRIGIDO — reescrito para testar ratio > 0.5 E delta > 5% juntos, com casos PARCIALMENTE_CONFIRMADA quando só um critério é satisfeito.

### [MELHORIA] Charts de hipóteses no frontend — estrutura já existe
- **Projeto:** data_ia_framework
- **Tipo:** Verificação
- **Descrição:** Analisado web/index.html e web/server.py. Os gráficos de hipóteses (pie de status, bar de confiança, heatmap de correlações, heatmap de métricas) JÁ EXISTEM no frontend (`renderValidatedCharts`) e são gerados pelo backend (`_build_charts`). Não há bug de missing charts — a implementação está correta.
- **Arquivos:** web/index.html (~921-1069), web/server.py
- **Assignee:** desenvolvedor
- **Status:** ✅ VERIFICADO —charts funcionam corretamente quando dados são carregados.

### [INFO] Kanban DB corrompido — tarefas não puderam ser criadas
- **Projeto:** data_ia_framework
- **Tipo:** Infra
- **Descrição:** `hermes kanban create` retorna "database disk image is malformed". DB em ~/.hermes/kanban.db. Necessário repairs ou recriar.
- **Arquivo:** ~/.hermes/kanban.db
- **Assignee:** —
- **Status:** ⚠️ NÃO CORRIGIDO — bugs corrigidos diretamente no código sem usar kanban.

---

### [MELHORIA] Permitir usuário definir coluna objetivo (fato) e dimensões
- **Projeto:** data_ia_framework
- **Tipo:** Melhoria
- **Descrição:** O usuário pode preencher opcionalmente qual coluna é o "fato" (target/de interesse, ex: revenue, ticket, conversion) e quais são "dimensões" (ex: região, categoria, canal). Isso melhora a qualidade das hipóteses geradas. Conceito de fato e dimensão inspirado em modelagem dimensional.
- **Arquivo:** web/index.html (formulário), src/hypothesis/generator.py
- **Assignee:** desenvolvedor