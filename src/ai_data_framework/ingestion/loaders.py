"""Loaders para diferentes fontes de dados."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import polars as pl
import yaml


class BaseLoader(ABC):
    """Classe base para loaders."""

    def __init__(self, source: str, **kwargs: Any) -> None:
        self.source = source
        self.options = kwargs

    @abstractmethod
    def load(self) -> pl.LazyFrame:
        """Carrega os dados como LazyFrame."""
        raise NotImplementedError

    def infer_quality(self, df: pl.LazyFrame) -> dict[str, Any]:
        """Infere métricas de qualidade dos dados."""
        schema = df.collect_schema()
        null_counts = df.collect().null_count()
        total_rows = df.collect().height
        total_cols = df.collect().width

        null_percent = {
            col: (null_counts[col].item() / total_rows * 100) if total_rows > 0 else 0
            for col in schema.names()
        }

        duplicate_rows = df.collect().height - df.collect().unique().height

        return {
            "total_rows": total_rows,
            "total_columns": total_cols,
            "null_percent": null_percent,
            "duplicate_rows": duplicate_rows,
            "data_types": {name: str(dtype) for name, dtype in schema.items()},
            "completeness_score": sum(null_percent.values()) / len(null_percent) if null_percent else 0,
        }


class CSVLoader(BaseLoader):
    """Loader para arquivos CSV."""

    def load(self) -> pl.LazyFrame:
        separator = self.options.get("separator", ",")
        has_header = self.options.get("has_header", True)
        encoding = self.options.get("encoding", "utf-8")
        try:
            return pl.scan_csv(
                self.source,
                separator=separator,
                has_header=has_header,
                encoding=encoding,
            )
        except Exception:
            return pl.scan_csv(self.source, separator=separator)


class ParquetLoader(BaseLoader):
    """Loader para arquivos Parquet."""

    def load(self) -> pl.LazyFrame:
        return pl.scan_parquet(self.source)


class ExcelLoader(BaseLoader):
    """Loader para arquivos Excel."""

    def load(self) -> pl.LazyFrame:
        sheet = self.options.get("sheet", 0)
        return pl.scan_excel(self.source, sheet_selection=sheet)


class SQLLoader(BaseLoader):
    """Loader para consultas SQL."""

    def load(self) -> pl.LazyFrame:
        # Placeholder para integração SQL
        # Requer DATABASE_URL configurado
        raise NotImplementedError("SQLLoader requires database configuration")


class YAMLConfigLoader(BaseLoader):
    """Loader para configurações YAML."""

    def load(self) -> dict[str, Any]:
        with open(self.source, "r") as f:
            return yaml.safe_load(f)


def get_loader(source: str, **kwargs: Any) -> BaseLoader:
    """Factory para obter o loader correto baseado na extensão."""
    ext = Path(source).suffix.lower()
    loaders = {
        ".csv": CSVLoader,
        ".parquet": ParquetLoader,
        ".xlsx": ExcelLoader,
        ".xls": ExcelLoader,
        ".yaml": YAMLConfigLoader,
        ".yml": YAMLConfigLoader,
    }
    loader_class = loaders.get(ext, CSVLoader)
    return loader_class(source, **kwargs)