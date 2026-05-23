# SPEC.md — AI Data Framework

## Paleta de Cores do Frontend

O frontend (`web/index.html`) utiliza a seguinte paleta de cores CSS (variáveis em `:root`):

### Base
| Variável | Valor | Uso |
|---|---|---|
| `--bg` | `#0f1117` | Fundo principal da página |
| `--surface` | `#1a1d27` | Cards, sidebar, top-bar |
| `--surface2` | `#21242f` | Hipóteses cards, insight cards, chart boxes |
| `--border` | `#2a2d3a` | Bordas de cards, inputs, tabelas |
| `--text` | `#e4e4e7` | Texto principal |
| `--text-dim` | `#71717a` | Texto secundário, labels, placeholders |

### Accent (Cyan)
| Variável | Valor | Uso |
|---|---|---|
| `--accent` | `#06b6d4` | Botão principal, links, badge-info, barra de progresso ativa |
| `--accent-dim` | `#0891b2` | Hover do botão principal |

### Status
| Variável | Valor | Uso |
|---|---|---|
| `--success` | `#22c55e` | Hipótese confirmada, badge-success, log success |
| `--warning` | `#eab308` | Hipótese parcial, badge-warning, type-date badge |
| `--danger` | `#ef4444` | Hipótese refutada, badge-danger, log error |

### Extra
| Variável | Valor | Uso |
|---|---|---|
| `--purple` | `#a855f7` | type-str badge |
| `--pink` | `#ec4899` | type-bool badge |

## Decisões de Design

1. **Paleta dark-mode GitHub-inspired mas com accent cyan** — Não usa o accent azul (#58a6ff) do GitHub; o cyan (#06b6d4) foi escolhido para identidade visual própria.
2. **Todas as cores são CSS custom properties** — Definidas em `:root`, facilitando manutenção e theming futuro.
3. **Badges com cor de fundo semi-transparente** — Usa `rgba()` para integração harmônica com backgrounds escuros.

## Estrutura do Frontend

- **Top-bar fixo** (sticky): upload + inputs de configuração + botão Executar
- **Sidebar**: navegação por seções, 280px de largura (Dados, Análise, Insights, Sistema)
- **Main content**: renderizado dinamicamente via JavaScript após execução do pipeline
- **Responsivo**: colapsa sidebar em bottom-nav em mobile
- **Assets**: CSS e JS inline no `web/index.html` (todos os estilos e scripts no mesmo arquivo)

## Seções da Interface

1. **Carregar Dados** — Upload de CSV/Parquet/Excel + Overview + Amostra + Qualidade
2. **Estrutura** — Colunas + Estatísticas + Gráficos
3. **Hipóteses** — Todas / Confirmadas / Refutadas / Parciais
4. **Validadas** — Hipóteses confirmadas + refutadas com seus charts
5. **Insights** — Lista + Gráficos
6. **Log** — Output do pipeline em tempo real

## Top Bar — Config Row

- Input de **Objetivo** (texto livre): "🎯 Qual é o problema de negócio?"
- Select de **Persona**: Analista, Gestor, Executivo, Dev
- Select de **LLM**: MiniMax, Claude, GPT-4, LiteLLM
- Botão **Executar**

## Stack

- Frontend: HTML/CSS/JS vanilla (sem frameworks), tudo inline em `web/index.html`
- Backend: Python (FastAPI ou Flask) servindo o arquivo estático
- Comunicação: HTTP REST + JSON