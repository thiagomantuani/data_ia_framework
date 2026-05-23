"""Audit logging para o pipeline analítico.

Cada passo do pipeline registra:
- input: dados de entrada
- output: dados de saída
- operation: operação aplicada
- timestamp: quando ocorreu
- version: versão do nó (hipótese, insight, etc.)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class OperationType(str, Enum):
    """Tipos de operação no pipeline."""

    LOAD = "load"
    PROFILE = "profile"
    GENERATE_HYPOTHESIS = "generate_hypothesis"
    VALIDATE_HYPOTHESIS = "validate_hypothesis"
    GENERATE_INSIGHT = "generate_insight"
    CREATE_DASHBOARD = "create_dashboard"
    TRANSFORM = "transform"


@dataclass
class AuditEntry:
    """Uma entrada de auditoria."""

    id: str
    operation: OperationType
    timestamp: str  # ISO 8601
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AuditLogger:
    """Logger de auditoria para o pipeline.

    Usage:
        logger = AuditLogger()
        logger.log(
            operation=OperationType.LOAD,
            input_data={"source": "dados.csv"},
            output_data={"rows": 1000, "cols": 20},
            metadata={"loader": "CSVLoader"},
        )
    """

    def __init__(self, output_dir: str | None = None) -> None:
        self.entries: list[AuditEntry] = []
        self._output_dir = output_dir

    def log(
        self,
        operation: OperationType,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Registra uma operação do pipeline.

        Returns:
            ID da entrada criada.
        """
        entry = AuditEntry(
            id=str(uuid.uuid4())[:8],
            operation=operation,
            timestamp=datetime.now(UTC).isoformat(),
            input_data=input_data,
            output_data=output_data,
            metadata=metadata or {},
        )
        self.entries.append(entry)
        return entry.id

    def get_chain(
        self,
        node_id: str | None = None,
        operation: OperationType | None = None,
    ) -> list[AuditEntry]:
        """Recupera cadeia de auditoria, opcionalmente filtrada."""
        results = self.entries
        if operation:
            results = [e for e in results if e.operation == operation]
        return results

    def to_dict(self) -> dict[str, Any]:
        """Serializa todos os entries para dict."""
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total": len(self.entries),
        }

    def export_json(self, path: str | None = None) -> str:
        """Exporta audit log para JSON.

        Args:
            path: caminho do arquivo. Se None, usa audit_log.json no dir do output
                  ou no diretório padrão ~/.ai-data/audit/.

        Returns:
            Caminho do arquivo escrito.
        """
        if path is None:
            base = self._output_dir or str(Path.home() / ".ai-data" / "audit")
            path = str(Path(base) / "audit_log.json")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return path

    def reproduce_state(self, operation_id: str) -> dict[str, Any] | None:
        """Tenta reproduzir um estado a partir de um ID de operação."""
        entry = next((e for e in self.entries if e.id == operation_id), None)
        if entry is None:
            return None
        return {
            "operation": entry.operation.value,
            "timestamp": entry.timestamp,
            "input": entry.input_data,
            "output": entry.output_data,
            "metadata": entry.metadata,
        }
