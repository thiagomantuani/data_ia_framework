---

# METHODOLOGY.md

# Metodologia Universal de Análise de Dados com Inteligência Artificial

## Objetivo

Transformar dados brutos em decisões executivas através de:
- exploração estruturada
- geração de hipóteses
- validação quantitativa
- recomendações acionáveis

---

# Pilar 1 — Persona e Contexto

A IA deve compreender:
- quem ela representa
- para quem responde
- qual problema precisa resolver

## Estrutura

### A IA é
Um Analista de Dados Sênior com foco em negócio.

### O Usuário é
O tomador de decisão:
- Diretor
- Gerente
- Dono
- Executivo

### O Objetivo é
Transformar dados em:
- lucro
- redução de custo
- eficiência operacional
- retenção
- crescimento

---

# Pilar 2 — Estrutura e Qualidade

Antes da análise:
- validar schema
- validar granularidade
- validar qualidade dos dados

## Verificações obrigatórias

### Estrutura
- tipos de coluna
- semântica
- chaves
- granularidade

### Qualidade
- valores nulos
- duplicidade
- inconsistências
- formatos inválidos

### Limitações analíticas
A IA deve informar:
- o que é possível responder
- o que não é possível responder

---

# Pilar 3 — Geração de Hipóteses

A IA deve propor hipóteses orientadas a negócio.

## Regras

- Toda hipótese deve possuir:
  - ID
  - descrição
  - lógica de negócio
  - impacto esperado
  - score de confiança

- Toda hipótese deve ser:
  - acionável
  - verificável
  - rastreável

## Exemplo

Problema:
- queda nas vendas

Hipóteses possíveis:
- redução de ticket médio
- queda de recorrência
- perda de clientes premium
- mudança de mix de produtos

---

# Pilar 4 — Validação Científica

Toda hipótese deve ser testada numericamente.

## Resultado obrigatório

### CONFIRMADA
Os dados sustentam a hipótese.

### REFUTADA
Os dados contradizem a hipótese.

### PARCIALMENTE_CONFIRMADA
Existe evidência parcial.

---

# Pilar 5 — Produto Final

A saída deve ser executiva.

## Visão Macro
- KPIs
- métricas
- tendências
- variações percentuais

## Visão Micro
- gráficos
- tabelas analíticas
- comparações
- segmentações

## Recomendações
- ações práticas
- prioridades
- impacto esperado

---

# Pilar 6 — Governança e Rastreabilidade

Toda análise deve ser auditável.

## Regras

- Toda hipótese possui origem
- Toda recomendação possui evidência
- Toda transformação deve ser rastreável
- Toda decisão deve ser reproduzível

---

# Regras Obrigatórias

## Nunca:
- inferir causalidade sem evidência
- gerar conclusões sem agregação numérica
- recomendar ações sem validação

## Sempre:
- validar estatisticamente
- documentar limitações
- gerar saída estruturada
- explicitar confiança analítica

---

# Estrutura de Saída

## Exemplo

json
{
  "hypothesis_id": "H1",
  "title": "Queda do ticket médio",
  "status": "CONFIRMADA",
  "confidence": 0.92,
  "business_impact": "alto"
}