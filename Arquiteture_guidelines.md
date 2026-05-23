---

# ARCHITECTURE_GUIDELINES.md

# Diretrizes Arquiteturais

## Objetivo

Garantir:
- consistência
- escalabilidade
- testabilidade
- observabilidade
- rastreabilidade

---

# 1. Separação de Responsabilidades

Nunca misturar:
- regra de negócio
- acesso a dados
- prompts
- visualização
- persistência

Cada módulo deve possuir responsabilidade única.

---

# 2. Tipagem Estrita

Toda entrada e saída deve ser tipada.

## Obrigatório
- mypy strict
- Protocol
- TypedDict
- dataclass
- Pydantic

## Proibido
- Any desnecessário
- dict sem tipagem
- retorno implícito

---

# 3. Modelagem de Domínio

Toda entidade deve possuir:
- identidade
- estado
- validação
- tipagem

## Exemplo

python
@dataclass(slots=True)
class Hypothesis:
    id: str
    title: str
    confidence: float