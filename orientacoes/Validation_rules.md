# Regras de Validação

## CONFIRMADA

Uma hipótese é **CONFIRMADA** quando todas as condições abaixo são satisfeitas:

1. **Diferença relevante** — o tamanho do efeito éstatisticamente significativo (p < 0.05) ou materialmente relevante para o negócio (delta > 5% do baseline)
2. **Consistência temporal** — o padrão se repete em mais de um período (dados trimestrais: ≥ 2 trimestres; dados mensais: ≥ 2 meses; dados diários: ≥ 7 dias)
3. **Evidência quantitativa** — há pelo menos 2 fontes independentes de dados confirmando o fenômeno

## REFUTADA

Uma hipótese é **REFUTADA** quando qualquer condição abaixo ocorre:

1. **Ausência de evidência** — não foi possível encontrar sinal nos dados após análise suficiente
2. **Comportamento inconsistente** — a relação observada não se mantém em subperíodos ou segmentos diferentes

## PARCIALMENTE_CONFIRMADA

Uma hipótese é **PARCIALMENTE_CONFIRMADA** quando:
- A direção do efeito está correta, mas a magnitude é menor que o esperado
- O padrão se verifica apenas em alguns segmentos ou períodos específicos

## Fluxo de validação

```
Hipótese criada
    ↓
Análise exploratória
    ↓
Teste estatístico / comparativo
    ↓
[CONFIRMADA] → Recomendação gerada
[REFUTADA] → Nova hipótese formulada
[PARCIALMENTE_CONFIRMADA] → Escopo refinado, nova análise
```