"""Tests for pit38_crypto.transform."""

import math

import pandas as pd
import pytest

from pit38_crypto.transform import NumericTransformer


def _make_df(**cols):
    return pd.DataFrame(cols)


def test_detects_euro_columns(raw_statement_df):
    t = NumericTransformer()
    cols = t._detect_currency_columns(raw_statement_df)
    expected = {
        "Price at Transaction",
        "Subtotal",
        "Total (inclusive of fees and/or spread)",
        "Fees and/or Spread",
    }
    assert expected.issubset(set(cols))


def test_non_euro_columns_not_detected(raw_statement_df):
    t = NumericTransformer()
    cols = t._detect_currency_columns(raw_statement_df)
    assert "Asset" not in cols
    assert "Transaction Type" not in cols
    assert "Quantity Transacted" not in cols


def test_positive_value_converted(raw_statement_df):
    t = NumericTransformer()
    result = t.apply(raw_statement_df)
    val = result.loc[0, "Total (inclusive of fees and/or spread)"]
    assert isinstance(val, float)
    assert val > 0


def test_negative_value_converted():
    df = _make_df(amount=["€1.00", "-€16.50", "€0.00"])
    t = NumericTransformer()
    result = t.apply(df)
    assert result.loc[0, "amount"] == pytest.approx(1.00)
    assert result.loc[1, "amount"] == pytest.approx(-16.50)
    assert result.loc[2, "amount"] == pytest.approx(0.00)


def test_non_euro_column_unchanged():
    df = _make_df(name=["Alice", "Bob"], score=[1, 2])
    t = NumericTransformer()
    result = t.apply(df)
    assert list(result["name"]) == ["Alice", "Bob"]
    assert list(result["score"]) == [1, 2]


def test_original_df_not_mutated(raw_statement_df):
    t = NumericTransformer()
    original_val = raw_statement_df.loc[0, "Total (inclusive of fees and/or spread)"]
    t.apply(raw_statement_df)
    assert raw_statement_df.loc[0, "Total (inclusive of fees and/or spread)"] == original_val


def test_custom_symbol():
    df = _make_df(price=["$10.00", "$-5.00", "$0.50"])
    t = NumericTransformer(currency_symbol="$")
    result = t.apply(df)
    assert result.loc[0, "price"] == pytest.approx(10.00)
    assert result.loc[1, "price"] == pytest.approx(-5.00)


def test_nan_preserved():
    df = _make_df(amount=["€1.00", None])
    t = NumericTransformer()
    result = t.apply(df)
    assert result.loc[0, "amount"] == pytest.approx(1.00)
    assert math.isnan(result.loc[1, "amount"])
