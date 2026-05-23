# Guia Prático de Fundamentos de Análise de Dados e Modelagem Estratégica

## 1. Definição do Problema de Negócio

### O que é:
Identificar a pergunta central e o objetivo macro que a empresa precisa responder. No exemplo prático do vídeo, a pergunta norteadora era: *"O faturamento da rede de cafeterias está aumentando? Se sim, quais são os principais motivos que estão impulsionando esse crescimento?"*

### Significado:
Sem um problema claro e bem delimitado, a análise de dados perde completamente a direção. É essa definição que separa o mero "apertador de botão" (que gera gráficos aleatórios e sem propósito) de um analista estratégico de alto nível, cujo trabalho gera impacto direto na receita ou na eficiência da operação.

---

## 2. Método Fato-Dimensão

Para estruturar qualquer análise de forma eficiente e organizar o pensamento analítico antes de manipular os dados, utilizamos o conceito de Fato e Dimensão. Essa estrutura permite entender não apenas os números, mas todo o contexto que os cerca.

### A Tabela Fato (O "O que aconteceu?")
A tabela fato armazena os acontecimentos históricos do negócio, ou seja, as transações financeiras e operacionais. Ela é composta majoritariamente por valores numéricos (métricas) que podem ser somados, calculados ou medidos, além de chaves de ligação (IDs).

*   Exemplos de Métricas na Fato: Valor da venda, quantidade de itens comprados, custo do produto, tempo de duração de um atendimento (ticket), avaliação de satisfação.
*   Em resumo: É onde guardamos o volume de dados transacionais gerados pelo dia a dia da empresa.

### As Dimensões (O "Como, quando, onde e quem?")
As dimensões fornecem o contexto descritivo e as características textuais para as métricas contidas na tabela fato. Elas respondem às perguntas periféricas que explicam as variações nos números macro.

*   Dimensão Tempo (Quando?): Ano, mês, dia da semana, hora do dia, trimestre, feriado.
*   Dimensão Local/Geografia (Onde?): Cidade, estado, filial, bairro, ID da estação de bike.
*   Dimensão Produto/Serviço (O que?): Nome do produto, categoria, tamanho, tipo de plano, tipo de bicicleta (elétrica ou padrão).
*   Dimensão Cliente/Usuário (Quem?): Nome, idade, tipo de cadastro (assinante anual ou cliente de passe diário), gênero.

---

## 3. Cruzamento Estratégico para Geração de Insights

Ao dominar o Método Fato-Dimensão, o analista consegue cruzar Métricas (Fatos) com Filtros (Dimensões) de maneira lógica para responder ao Problema de Negócio definido na Etapa 1.

*   *Pergunta de Negócio:* O faturamento aumentou?
    *   Análise Fato-Dimensão: Somar o Valor da Venda (Fato) e agrupar pelo Mês/Ano (Dimensão Tempo) para verificar a curva de crescimento.
*   *Pergunta de Negócio:* Quais fatores impulsionaram o faturamento?
    *   Análise Fato-Dimensão 1: Agrupar o Faturamento (Fato) pela Categoria do Produto (Dimensão Produto) para descobrir qual setor mais vendeu.
    *   Análise Fato-Dimensão 2: Contar o Número de Transações (Fato) pelo Horário Comercial (Dimensão Tempo) para descobrir os picos operacionais de demanda.

Este fluxo garante que a Inteligência Artificial, quando utilizada como co-analista, construa códigos SQL ou scripts Python focados puramente nas intersecções que trazem valor e alavancas reais para a tomada de decisão do gestor.
