"""Verificação de privacidade e detecção de PII em datasets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import polars as pl


# Padrões regex para tipos comuns de PII
PII_PATTERNS: dict[str, re.Pattern] = {
    # Brasil
    "cpf": re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b"),
    "cnpj": re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "telefone_br": re.compile(r"\b\(?\d{2}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}\b"),
    "cep": re.compile(r"\b\d{5}-?\d{3}\b"),
    # Geral
    "telefone": re.compile(r"\b\d{7,15}\b"),
    "senha": re.compile(r"(?i)(password|senha|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE),
    "token": re.compile(r"(?i)(api_key|apikey|token|auth)\s*[:=]\s*[\w-]{10,}", re.IGNORECASE),
    "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    "mae": re.compile(r"(?i)\b(nome\s+da?\s+(mãe|mama)|maternal)\b"),
}


# Colunas que tendem a conter PII pelo nome
PII_COLUMN_NAMES: list[re.Pattern] = [
    re.compile(r"(?i)^(cpf|cnpj|email|telefone|phone|endereço|address|cep|zip|bairro|"
              r"nome|name|sobrenome|surname|apelido|nickname|senha|password|passwd|"
              r"rg|identidade|documento|cpf_resp|cnpj_resp|telefone_fixo|telefone_cel|"
              r"celular|mobile|idade|birth|nascimento|datanascimento|dt_nasc|sexo|gender|"
              r"cpf_func|cnpj_func|funcionario|cliente|customer|usuario|user)$"),
]


@dataclass
class PIIFinding:
    """Encontrado de PII numa coluna."""

    column: str
    pii_type: str
    pattern_matched: str
    sample_values: list[str] = field(default_factory=list)
    risk_level: str = "HIGH"  # HIGH, MEDIUM, LOW

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "pii_type": self.pii_type,
            "pattern": self.pattern_matched,
            "sample_values": self.sample_values,
            "risk_level": self.risk_level,
        }


class PIIDetector:
    """Deteta colunas que contêm PII num dataset."""

    def __init__(self, df: pl.LazyFrame | pl.DataFrame) -> None:
        self.df = df

    def _collect(self) -> pl.DataFrame:
        return self.df.collect() if isinstance(self.df, pl.LazyFrame) else self.df

    def detect_by_column_name(self) -> list[PIIFinding]:
        """Deteta PII pelo nome das colunas (baixa precisão, alta cobertura)."""
        findings: list[PIIFinding] = []
        collected = self._collect()
        schema = collected.collect_schema()

        for col_name in schema.names():
            for pattern in PII_COLUMN_NAMES:
                if pattern.search(col_name):
                    findings.append(PIIFinding(
                        column=col_name,
                        pii_type="COLUMN_NAME_MATCH",
                        pattern_matched=pattern.pattern,
                        risk_level="MEDIUM",
                    ))
                    break  # uma coluna = uma finding

        return findings

    def detect_by_content_sample(
        self,
        max_sample: int = 100,
        min_match_ratio: float = 0.1,
    ) -> list[PIIFinding]:
        """Deteta PII por análise de conteúdo (amostragem)."""
        findings: list[PIIFinding] = []
        collected = self._collect().slice(0, max_sample)
        schema = collected.collect_schema()

        for col_name, dtype in schema.items():
            # Só verificar colunas de texto/string
            if dtype not in (pl.Utf8, pl.String):
                continue

            col_values = collected[col_name].drop_nulls().to_list()
            if not col_values:
                continue

            str_values = [str(v) for v in col_values]
            total = len(str_values)

            for pii_type, pattern in PII_PATTERNS.items():
                matches = sum(1 for v in str_values if pattern.search(str(v)))
                ratio = matches / total if total > 0 else 0

                if ratio >= min_match_ratio:
                    sample_values = [
                        str(v) for v in str_values if pattern.search(str(v))
                    ][:5]

                    risk = "HIGH" if pii_type in (
                        "cpf", "cnpj", "credit_card", "senha", "token"
                    ) else "MEDIUM"

                    findings.append(PIIFinding(
                        column=col_name,
                        pii_type=pii_type,
                        pattern_matched=pattern.pattern,
                        sample_values=sample_values,
                        risk_level=risk,
                    ))

        return findings

    def scan(self) -> dict[str, Any]:
        """Executa scan completo de PII no dataset.

        Returns:
            Dict com colunas_pii (lista de findings) e has_pii (bool).
        """
        by_name = self.detect_by_column_name()
        by_content = self.detect_by_content_sample()

        # Combina — content采样 tem prioridade (mais preciso)
        findings_map: dict[str, PIIFinding] = {}

        for f in by_content:
            findings_map[f.column] = f

        for f in by_name:
            if f.column not in findings_map:
                findings_map[f.column] = f

        findings = list(findings_map.values())

        return {
            "pii_columns": [f.to_dict() for f in findings],
            "has_pii": len(findings) > 0,
            "pii_count": len(findings),
            "high_risk_count": sum(1 for f in findings if f.risk_level == "HIGH"),
        }

    def get_pii_columns(self) -> list[str]:
        """Retorna lista de nomes de colunas com PII."""
        return list(set(f.column for f in self.detect_by_content_sample()))


@dataclass
class PrivacyReport:
    """Relatório de privacidade do dataset."""

    has_pii: bool
    pii_columns: list[str]
    pii_findings: list[dict[str, Any]]
    recommended_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_pii": self.has_pii,
            "pii_columns": self.pii_columns,
            "pii_findings": self.pii_findings,
            "recommended_actions": self.recommended_actions,
        }


def check_dataset_privacy(df: pl.LazyFrame | pl.DataFrame) -> PrivacyReport:
    """Função utilitária para verificar privacidade de um dataset."""
    detector = PIIDetector(df)
    result = detector.scan()

    actions: list[str] = []
    if result["has_pii"]:
        actions.append(
            "Colunas com PII detectadas: remover ou anonimizar antes de exportar dashboard."
        )
        high_risk = result["high_risk_count"]
        if high_risk > 0:
            actions.append(
                f"{high_risk} colunas de alto risco identificadas — tratar com urgência."
            )

    return PrivacyReport(
        has_pii=result["has_pii"],
        pii_columns=detector.get_pii_columns(),
        pii_findings=result["pii_columns"],
        recommended_actions=actions,
    )