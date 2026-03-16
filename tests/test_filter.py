"""Tests for pit38_crypto.filter."""

import pandas as pd
import pytest

from pit38_crypto.filter import TransactionFilter


def test_default_rules_keep_buy_types(raw_statement_df):
    f = TransactionFilter()
    result = f.apply(raw_statement_df)
    assert set(result["Transaction Type"].unique()) == {"Advanced Trade Buy", "Buy"}


def test_default_rules_row_count(raw_statement_df):
    f = TransactionFilter()
    result = f.apply(raw_statement_df)
    # Sample has 7 Advanced Trade Buy + 1 Buy = 8 rows
    assert len(result) == 8


def test_excludes_other_types(raw_statement_df):
    f = TransactionFilter()
    result = f.apply(raw_statement_df)
    excluded = {"Retail Staking Transfer", "Deposit", "Staking Income", "Wrap Asset"}
    assert not excluded.intersection(set(result["Transaction Type"].unique()))


def test_index_is_reset(raw_statement_df):
    f = TransactionFilter()
    result = f.apply(raw_statement_df)
    assert list(result.index) == list(range(len(result)))


def test_custom_rule_injection(raw_statement_df):
    rule = lambda df: df["Asset"] == "BTC"
    f = TransactionFilter(rules=[rule])
    result = f.apply(raw_statement_df)
    assert all(result["Asset"] == "BTC")


def test_multiple_rules_are_anded(raw_statement_df):
    rule_buy = lambda df: df["Transaction Type"].isin(["Advanced Trade Buy", "Buy"])
    rule_btc = lambda df: df["Asset"] == "BTC"
    f = TransactionFilter(rules=[rule_buy, rule_btc])
    result = f.apply(raw_statement_df)
    assert all(result["Asset"] == "BTC")
    assert all(result["Transaction Type"].isin(["Advanced Trade Buy", "Buy"]))


def test_empty_result_when_no_match(raw_statement_df):
    rule = lambda df: df["Asset"] == "NONEXISTENT"
    f = TransactionFilter(rules=[rule])
    result = f.apply(raw_statement_df)
    assert len(result) == 0
