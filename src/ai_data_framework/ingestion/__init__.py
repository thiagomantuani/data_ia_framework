"""Ingestion - carregamento de dados."""

from ai_data_framework.ingestion.loaders import CSVLoader, ParquetLoader, ExcelLoader, SQLLoader

__all__ = ["CSVLoader", "ParquetLoader", "ExcelLoader", "SQLLoader"]