"""Gerador de hipóteses de negócio — focado em negócios, não em estatísticas."""

from __future__ import annotations

import uuid
from typing import Any

import polars as pl

from ai_data_framework.core.entities import Hypothesis, HypothesisStatus


class HypothesisGenerator:
    """Gera hipóteses de negócio a partir de profiling de dados."""

    def __init__(self, profiling_results: dict[str, Any]) -> None:
        self.profiling = profiling_results

    def generate(self, problem_statement: str | None = None) -> list[Hypothesis]:
        """Gera hipóteses de NEGÓCIO (não técnicas/estatísticas).

        Exemplos de hipóteses de negócio:
        - "Adicionar pão de queijo ao pedido aumenta ticket médio em R$12"
        - "Clientes com score < 4.0 churnam 3x mais"
        - "Região Norte tem receita 40% abaixo da média"
        - "Clientes que compram mais de 3 itens têm 2x mais chance de voltar"
        - "Cupons de desconto atraem novos clientes mas reduzem margem"
        """
        hypotheses: list[Hypothesis] = []

        if not self.profiling:
            return hypotheses

        col_stats = self.profiling.get("column_stats", {})
        quality = self.profiling.get("quality_metrics", {})
        correlations = self.profiling.get("correlations", {})
        column_names = list(col_stats.keys())

        # Detect what type of business this is from column names
        business_type = self._detect_business_type(column_names)

        # === HIPÓTESES DE RECEITA / VENDAS ===
        hypotheses.extend(self._revenue_hypotheses(col_stats, correlations, business_type))

        # === HIPÓTESES DE CLIENTES / CHURN ===
        hypotheses.extend(self._customer_hypotheses(col_stats, correlations, business_type))

        # === HIPÓTESES DE REGIÃO / LOCALIZAÇÃO ===
        hypotheses.extend(self._regional_hypotheses(col_stats, correlations, business_type))

        # === HIPÓTESES DE PRODUTO / CATEGORIA ===
        hypotheses.extend(self._product_hypotheses(col_stats, correlations, business_type))

        # === HIPÓTESES DE SATISFAÇÃO ===
        hypotheses.extend(self._satisfaction_hypotheses(col_stats, correlations, business_type))

        # === HIPÓTESES DE TEMPORALIDADE ===
        hypotheses.extend(self._temporal_hypotheses(col_stats, business_type))

        # === HIPÓTESES DE OPORTUNIDADE / CRESCIMENTO ===
        hypotheses.extend(self._growth_hypotheses(col_stats, correlations, business_type))

        # Limitar a 12 hipóteses mais relevantes
        hypotheses = hypotheses[:12]

        return hypotheses

    def _detect_business_type(self, column_names: list[str]) -> dict[str, Any]:
        """Detecta o tipo de negócio baseado nos nomes das colunas."""
        cols_lower = [c.lower() for c in column_names]

        business_type = "varejo"  # default

        keywords = {
            "cafeteria": ["bebida", "cafe", "coffee", "pastel", "suco", "lanche"],
            "restaurante": ["prato", "mesa", "garcom", "conta", "comanda"],
            "e-commerce": ["pedido", "frete", "entrega", "carrinho", "checkout"],
            "saas": ["assinatura", "plan", "subscription", "monthly", "annual"],
            "marketplace": ["vendedor", "anunciante", "taxa", "comissao"],
        }

        for btype, kws in keywords.items():
            if any(kw in " ".join(cols_lower) for kw in kws):
                business_type = btype
                break

        return {"type": business_type, "columns": column_names}

    def _revenue_hypotheses(
        self, col_stats: dict, correlations: dict, business: dict
    ) -> list[Hypothesis]:
        """Hipóteses sobre receita e vendas."""
        hyps = []

        # Check for revenue column
        revenue_col = self._find_column(col_stats.keys(), ["revenue", "valor", "total", "venda"])
        cost_col = self._find_column(col_stats.keys(), ["cost", "custo", "despesa"])
        quantity_col = self._find_column(col_stats.keys(), ["quantity", "qtd", "quantidade", "itens"])

        if revenue_col:
            stats = col_stats.get(revenue_col, {})

            # Ticket médio / comportamento de compra
            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title="Ticket médio varia por comportamento de compra",
                description="Clientes que adicionam itens complementares têm ticket significativamente maior",
                business_logic="Oferecer sugestões de itens complementares no momento da compra pode aumentar o ticket em 15-25%",
                expected_impact="Alto",
                confidence=0.6,
                priority=1,
            ))

            # Margem de lucro
            if cost_col:
                hyps.append(Hypothesis(
                    id=str(uuid.uuid4())[:8],
                    title="Margem de lucro varia por categoria de produto",
                    description="Algumas categorias têm margem maior que outras — focar em produtos de alta margem pode melhorar rentabilidade",
                    business_logic="Identificar categorias de alta margem e priorizá-las no mix de vendas",
                    expected_impact="Alto",
                    confidence=0.7,
                    priority=1,
                ))

            # Quantidade e ticket
            if quantity_col:
                hyps.append(Hypothesis(
                    id=str(uuid.uuid4())[:8],
                    title="Clientes que compram mais itens têm ticket médio maior",
                    description="Existe correlação entre quantidade de itens por transação e valor total",
                    business_logic="Estratégias de cross-sell e upsell podem aumentar o volume por transação",
                    expected_impact="Médio",
                    confidence=0.6,
                    priority=2,
                ))

        return hyps

    def _customer_hypotheses(
        self, col_stats: dict, correlations: dict, business: dict
    ) -> list[Hypothesis]:
        """Hipóteses sobre clientes e churn."""
        hyps = []

        churn_col = self._find_column(col_stats.keys(), ["churn", "cancel", "abandono", "lost"])
        satisfaction_col = self._find_column(col_stats.keys(), ["satisfaction", "nota", "score", "avaliacao"])
        customer_col = self._find_column(col_stats.keys(), ["customer", "cliente", "user"])

        if satisfaction_col:
            stats = col_stats.get(satisfaction_col, {})
            mean_score = stats.get("mean", 0)

            # Score de satisfação e impacto em churn/retenção
            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title="Clientes insatisfeitos (score < 4.0) têm taxa de churn significativamente maior",
                description=f"Score médio atual é {mean_score:.1f}/5 — clientes abaixo disso têm maior propensão ao abandono",
                business_logic="Identificar clientes insatisfeitos permite ação proativa de retenção (offer, desconto, contato)",
                expected_impact="Alto",
                confidence=0.7,
                priority=1,
            ))

            # Satisfação e recorrência
            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title="Clientes satisfeitos (score > 4.5) compram com maior frequência",
                description="Clientes com alta satisfação tendem a comprar mais vezes no mesmo período",
                business_logic="Focar em Satisfação para melhorar recorrência e LTV do cliente",
                expected_impact="Médio",
                confidence=0.6,
                priority=2,
            ))

        if satisfaction_col and churn_col:
            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title="Clientes novos têm maior risco de churn nos primeiros 30 dias",
                description="Período inicial é crítico para retenção — onboarding deficient leads a abandono",
                business_logic="Programa de onboarding e primeira experiência positiva reduz churn inicial",
                expected_impact="Alto",
                confidence=0.5,
                priority=2,
            ))

        if customer_col:
            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title="Clientes recorrentes geram mais receita que clientes novos",
                description="Clientes existentes têm ticket médio maior e menor custo de aquisição",
                business_logic="Investir em retenção e fidelidade tem ROI superior a aquisição de novos clientes",
                expected_impact="Alto",
                confidence=0.7,
                priority=1,
            ))

        return hyps

    def _regional_hypotheses(
        self, col_stats: dict, correlations: dict, business: dict
    ) -> list[Hypothesis]:
        """Hipóteses sobre regiões/geografia."""
        hyps = []

        region_col = self._find_column(col_stats.keys(), ["region", "regiao", "cidade", "estado", "bairro"])
        revenue_col = self._find_column(col_stats.keys(), ["revenue", "valor", "total"])

        if region_col:
            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title="Receita varia significativamente por região",
                description="Algumas regiões têm performance acima ou abaixo da média — entender motivos permite ação",
                business_logic="Regiões com baixa performance podem se beneficiar de estratégias regionalizadas (mix de produtos, preços, promoções)",
                expected_impact="Alto",
                confidence=0.6,
                priority=1,
            ))

            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title="Regiões com maior volume de clientes concentram mais receita",
                description="Regiões com mais clientes nem sempre são as de maior receita — entender conversão é chave",
                business_logic="Analisar eficiência de conversão por região para otimizar investimento",
                expected_impact="Médio",
                confidence=0.5,
                priority=2,
            ))

        return hyps

    def _product_hypotheses(
        self, col_stats: dict, correlations: dict, business: dict
    ) -> list[Hypothesis]:
        """Hipóteses sobre produtos/categorias."""
        hyps = []

        product_col = self._find_column(col_stats.keys(), ["product", "produto", "categoria", "category", "tipo"])
        revenue_col = self._find_column(col_stats.keys(), ["revenue", "valor", "total"])

        if product_col:
            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title="Certain categorias de produto têm maior rentabilidade",
                description="Nem todos os produtos contribuem igualmente para o lucro — algumas categorias são mais estratégicas",
                business_logic="Focar em categorias de alta rentabilidade no mix de vendas e em promoções",
                expected_impact="Alto",
                confidence=0.6,
                priority=1,
            ))

            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title="Clientes que compram categorias diversas têm maior lifetime value",
                description="Cross-category clients tem maior retenção e valor no longo prazo",
                business_logic="Estratégias de bundling e cross-categorias aumentam LTV",
                expected_impact="Médio",
                confidence=0.5,
                priority=2,
            ))

        return hyps

    def _satisfaction_hypotheses(
        self, col_stats: dict, correlations: dict, business: dict
    ) -> list[Hypothesis]:
        """Hipóteses sobre satisfação."""
        hyps = []

        satisfaction_col = self._find_column(col_stats.keys(), ["satisfaction", "nota", "score", "avaliacao"])

        if satisfaction_col:
            hyps.append(Hypothesis(
                id=str(uuid.uuid4())[:8],
                title="Clientes com satisfação entre 4.0-4.5 são os que mais pedem reembolso/cancelamento",
                description="O ponto médio é perigoso — clientes razoavelmente satisfeitos mas não encantandos",
                business_logic="Programa de encantamento para clientes no faixa 4.0-4.5 pode reduzir cancelamentos",
                expected_impact="Alto",
                confidence=0.5,
                priority=2,
            ))

        return hyps

    def _temporal_hypotheses(
        self, col_stats: dict, business: dict
    ) -> list[Hypothesis]:
        """Hipóteses sobre temporalidade."""
        hyps = []

        timestamp_col = self._find_column(col_stats.keys(), ["timestamp", "date", "data", "hora", "time"])

        hyps.append(Hypothesis(
            id=str(uuid.uuid4())[:8],
            title="Receita apresenta variação por período (dia/semana/mês)",
            description="Identificar sazonalidade permite planejamento de estoque, staffing e campanhas",
            business_logic="Sazonalidade bem explorada pode aumentar receita em 10-20% em períodos altos",
            expected_impact="Alto",
            confidence=0.5,
            priority=2,
        ))

        hyps.append(Hypothesis(
            id=str(uuid.uuid4())[:8],
            title="Horário de pico concentra 60% das vendas",
            description="Se existe horário de pico, otimizar staffing nesse período aumenta eficiência",
            business_logic="Match de oferta com demanda reduz waiting time e melhora satisfação",
            expected_impact="Médio",
            confidence=0.5,
            priority=3,
        ))

        return hyps

    def _growth_hypotheses(
        self, col_stats: dict, correlations: dict, business: dict
    ) -> list[Hypothesis]:
        """Hipóteses de crescimento/oportunidade."""
        hyps = []

        # Oportunidade de upsell
        hyps.append(Hypothesis(
            id=str(uuid.uuid4())[:8],
            title="Adicionar item complementar ao pedido aumenta ticket médio em 15-25%",
            description="Cross-sell bem executado aumenta revenue sem aumentar custo de aquisição",
            business_logic="Treinar equipe/vender sugestões de Add-on no momento da compra",
            expected_impact="Alto",
            confidence=0.7,
            priority=1,
        ))

        # Oportunidade de recorrência
        hyps.append(Hypothesis(
            id=str(uuid.uuid4())[:8],
            title="Programa de fidelidade pode aumentar recorrência em 20%",
            description="Clientes em programa de fidelidade compram mais frequentemente",
            business_logic="Investir em programa de pontos/recompensas para aumentar recorrência",
            expected_impact="Alto",
            confidence=0.6,
            priority=2,
        ))

        return hyps

    def _find_column(self, columns: list[str], keywords: list[str]) -> str | None:
        """Encontra coluna que corresponde a uma das keywords."""
        for col in columns:
            col_lower = col.lower()
            for kw in keywords:
                if kw in col_lower:
                    return col
        return None

    def prioritize(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        """Ordena hipóteses por prioridade (impacto + confiança)."""
        return sorted(
            hypotheses,
            key=lambda h: (h.priority, -h.confidence),
        )