"""Testes para ingestion."""

import polars as pl
import pytest

from ai_data_framework.ingestion.loaders import (
    CSVLoader,
    ParquetLoader,
    get_loader,
)


def test_csv_loader(tmp_path):
    """Testa CSVLoader."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("name,value\nA,1\nB,2\nC,3")

    loader = CSVLoader(str(csv_file))
    df = loader.load()

    assert isinstance(df, pl.LazyFrame)
    assert df.collect().height == 3
    assert df.collect().width == 2


def test_parquet_loader(tmp_path):
    """Testa ParquetLoader."""
    parquet_file = tmp_path / "test.parquet"
    df = pl.DataFrame({"name": ["A", "B"], "value": [1, 2]})
    df.write_parquet(parquet_file)

    loader = ParquetLoader(str(parquet_file))
    loaded = loader.load()

    assert isinstance(loaded, pl.LazyFrame)
    assert loaded.collect().height == 2


def test_get_loader_csv():
    """Testa factory get_loader para CSV."""
    loader = get_loader("file.csv")
    assert isinstance(loader, CSVLoader)


def test_get_loader_parquet():
    """Testa factory get_loader para Parquet."""
    loader = get_loader("file.parquet")
    assert isinstance(loader, ParquetLoader)


def test_infer_quality():
    """Testa inferência de qualidade."""
    csv_file = "/tmp/test_quality.csv"
    with open(csv_file, "w") as f:
        f.write("a,b,c\n1,2,\n4,,5\n7,8,9")

    loader = CSVLoader(csv_file)
    df = loader.load()
    quality = loader.infer_quality(df)

    assert quality["total_rows"] == 3
    assert quality["total_columns"] == 3
    assert "a" in quality["null_percent"]