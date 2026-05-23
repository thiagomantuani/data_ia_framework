# Governança

## Recomendações

Toda recomendação deve:
- **Apontar evidência numérica** — métricas, valores, porcentagens que sustentam a conclusão
- **Apontar hipótese associada** — cada recomendação é derivada de uma hipótese validada (ou refutada)
- **Possuir rastreabilidade** — caminho inverso: recomendação → validação → hipótese → dado original

## Transformações

Toda transformação de dados deve ser **auditável**:
- Cada passo do pipeline deve registrar: input, output, operação aplicada, timestamp
- Nenhuma transformação pode ocorrer sem log de auditoria
- O pipeline deve ser capaz de reproduzir qualquer estado intermediário a partir do dado bruto

## Rastreabilidade

```
Dado Bruto → Hipótese Gerada → Validação → Insight → Recomendação
     ↑             ↑              ↑           ↑           ↑
  [origem]    [generator]    [validator] [llm]    [executivo]
```

Cada nó desse grafo deve ser versionado e consultável.
