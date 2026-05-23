"""Cliente LLM para geração de hipóteses e insights."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Literal

import httpx


class BaseLLMClient(ABC):
    """Classe base para clientes LLM."""

    def __init__(self, api_key: str, model: str, **kwargs: Any) -> None:
        self.api_key = api_key
        self.model = model
        self.extra = kwargs

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Gera texto a partir de prompt."""
        raise NotImplementedError


class AnthropicClient(BaseLLMClient):
    """Cliente para Anthropic Claude."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> None:
        super().__init__(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", ""),
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        """Gera texto usando Anthropic Claude."""
        if not self.api_key:
            return self._fallback_response(prompt)

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        messages = [{"role": "user", "content": prompt}]
        if system:
            messages.insert(0, {"role": "assistant", "content": system})

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "messages": messages,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["content"][0]["text"]
        except httpx.HTTPError as e:
            return f"[Anthropic Error: {e}]"

    def _fallback_response(self, prompt: str) -> str:
        return f"[Anthropic] Simulating response for: {prompt[:80]}..."


class OpenAIClient(BaseLLMClient):
    """Cliente para OpenAI GPT."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> None:
        super().__init__(
            api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        """Gera texto usando OpenAI GPT."""
        if not self.api_key:
            return self._fallback_response(prompt)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "messages": messages,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            return f"[OpenAI Error: {e}]"

    def _fallback_response(self, prompt: str) -> str:
        return f"[OpenAI] Simulating response for: {prompt[:80]}..."


class MiniMaxClient(BaseLLMClient):
    """Cliente para MiniMax (modelo MiniMax-M2.7)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "MiniMax-M2.7",
        group_id: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> None:
        super().__init__(
            api_key=api_key or os.environ.get("MINIMAX_API_KEY", ""),
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        self.group_id = group_id or os.environ.get("MINIMAX_GROUP_ID", "")
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        """Gera texto usando MiniMax API."""
        if not self.api_key or not self.group_id:
            return self._fallback_response(prompt)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "messages": messages,
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    "https://api.minimax.chat/v1/text/chatcompletion_v2",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            return f"[MiniMax Error: {e}]"
        except (KeyError, IndexError) as e:
            return f"[MiniMax Parse Error: {e}] - {response.text[:200] if 'response' in dir() and hasattr(response, 'text') else 'no response'}"

    def _fallback_response(self, prompt: str) -> str:
        return f"[MiniMax] Simulating response for: {prompt[:80]}..."


class LiteLLMClient(BaseLLMClient):
    """Cliente para LiteLLM (suporta múltiplos providers)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "anthropic/claude-sonnet-4-20250514",
        base_url: str = "http://localhost:4000",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> None:
        super().__init__(
            api_key=api_key or os.environ.get("LITELLM_API_KEY", "dummy"),
            model=model,
            base_url=base_url,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        """Gera texto via LiteLLM proxy."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "messages": messages,
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            return f"[LiteLLM Error: {e}]"


class LLMClient:
    """Facede para clientes LLM com factory."""

    PROVIDERS: dict[str, type[BaseLLMClient]] = {
        "anthropic": AnthropicClient,
        "openai": OpenAIClient,
        "minimax": MiniMaxClient,
        "litellm": LiteLLMClient,
    }

    def __init__(
        self,
        provider: Literal["anthropic", "openai", "minimax", "litellm"] = "minimax",
        model: str | None = None,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.provider = provider
        client_class = self.PROVIDERS.get(provider)

        if not client_class:
            raise ValueError(f"Provider '{provider}' não suportado. Use: {list(self.PROVIDERS.keys())}")

        model_defaults: dict[str, str] = {
            "anthropic": "claude-sonnet-4-20250514",
            "openai": "gpt-4o",
            "minimax": "MiniMax-M2.7",
            "litellm": "anthropic/claude-sonnet-4-20250514",
        }

        self.client = client_class(
            api_key=api_key,
            model=model or model_defaults.get(provider, ""),
            **kwargs,
        )

    def generate(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        """Gera texto."""
        return self.client.generate(prompt, system=system, **kwargs)

    def generate_hypotheses(
        self,
        problem_statement: str,
        profiling_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Gera hipóteses usando LLM com prompt estruturado."""
        system = """Você é um Analista de Dados Sênior especializado em gerar hipóteses de negócio acionáveis.
Cada hipótese deve ter:
- ID único (H1, H2, etc.)
- Título claro
- Descrição breve
- Lógica de negócio
- Impacto esperado (Alto/Médio/Baixo)
- Score de confiança inicial (0.0 a 1.0)

Responda APENAS com JSON array, sem texto adicional."""

        prompt = f"""Problema de negócio: {problem_statement}

Resumo do profiling de dados:
- Total de linhas: {profiling_summary.get('quality_metrics', {}).get('total_rows', 'N/A')}
- Total de colunas: {profiling_summary.get('quality_metrics', {}).get('total_columns', 'N/A')}
- Completude: {profiling_summary.get('quality_metrics', {}).get('completeness_score', 'N/A')}%
- Colunas com nulos: {profiling_summary.get('quality_metrics', {}).get('null_percent', {})}
- Sugestões: {profiling_summary.get('suggestions', [])}

Gere 5 hipóteses de negócio no formato:
[
  {{
    "id": "H1",
    "title": "...",
    "description": "...",
    "business_logic": "...",
    "expected_impact": "Alto",
    "confidence": 0.5
  }}
]"""

        try:
            response = self.generate(prompt, system=system)
            # Try to parse as JSON
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            return json.loads(response)
        except (json.JSONDecodeError, Exception):
            return self._fallback_hypotheses()

    def _fallback_hypotheses(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "H1",
                "title": "Queda no ticket médio",
                "description": "Verificar se houve redução no valor médio por transação",
                "business_logic": "Redução de ticket indica menor volume de compra por cliente",
                "expected_impact": "Alto",
                "confidence": 0.5,
            },
            {
                "id": "H2",
                "title": "Perda de recorrência",
                "description": "Clientes estão comprando com menor frequência",
                "business_logic": "Queda na recorrência reduz revenue previsível",
                "expected_impact": "Alto",
                "confidence": 0.5,
            },
        ]

    def generate_insights(
        self,
        hypothesis: dict[str, Any],
        validation_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Gera insights executivos a partir de hipótese validada."""
        system = """Você é um Analista de Dados Sênior que transforma validações de hipóteses em insights executivos.
Forneça:
- Título do insight
- Descrição clara
- Métricas chave
- Recomendações acionáveis (3-5)
- Impacto no negócio (Alto/Médio/Baixo)
- Confiança (0.0 a 1.0)

Responda APENAS com JSON válido."""

        prompt = f"""Hipótese: {hypothesis.get('title', 'N/A')}
Descrição: {hypothesis.get('description', 'N/A')}
Status: {validation_results.get('status', 'N/A')}
Confiança: {validation_results.get('confidence', 0):.0%}
Evidência: {validation_results.get('evidence', 'N/A')}
Métricas: {validation_results.get('metrics', {})}

Gere insight executivo no formato:
{{
  "title": "...",
  "description": "...",
  "metrics": {{...}},
  "recommendations": ["...", "..."],
  "business_impact": "Alto",
  "confidence": 0.85
}}"""

        try:
            response = self.generate(prompt, system=system)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            return json.loads(response)
        except (json.JSONDecodeError, Exception):
            return {
                "title": f"Insight: {hypothesis.get('title', 'N/A')}",
                "description": "Insight gerado automaticamente",
                "metrics": validation_results.get("metrics", {}),
                "recommendations": ["Recomendação 1", "Recomendação 2"],
                "business_impact": hypothesis.get("expected_impact", "Médio"),
                "confidence": validation_results.get("confidence", 0.5),
            }