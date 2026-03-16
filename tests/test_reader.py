"""Tests for pit38_crypto.reader."""

import pandas as pd
import pytest

from pit38_crypto.reader import read_statement


def test_skips_metadata_rows(statement_csv):
    df = read_statement(statement_csv)
    assert list(df.columns[:4]) == ["ID", "Timestamp", "Transaction Type", "Asset"]


def test_row_count(statement_csv):
    df = read_statement(statement_csv)
    assert len(df) == 10


def test_timestamp_is_utc_datetime(statement_csv):
    df = read_statement(statement_csv)
    assert pd.api.types.is_datetime64_any_dtype(df["Timestamp"])
    assert str(df["Timestamp"].dt.tz) == "UTC"


def test_timestamp_values(statement_csv):
    df = read_statement(statement_csv)
    first_ts = df.loc[0, "Timestamp"]
    assert first_ts.year == 2025
    assert first_ts.month == 1
    assert first_ts.day == 13
