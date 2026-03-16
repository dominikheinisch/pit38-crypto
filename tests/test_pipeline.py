"""Tests for pit38_crypto.pipeline and the CLI."""

import os
import tempfile

import pandas as pd
import pytest
from click.testing import CliRunner

from pit38_crypto.cli import main
from pit38_crypto.currency import CurrencyMerger, FileCurrencySource
from pit38_crypto.filter import TransactionFilter
from pit38_crypto.pipeline import Pipeline, ALL_STEPS
from pit38_crypto.reader import read_statement
from tests.conftest import SAMPLE_STATEMENT_CSV, SAMPLE_RATES_CSV


def _read(content, suffix=".csv"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(content)
        yield path
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Pipeline unit tests
# ---------------------------------------------------------------------------

class TestPipeline:
    def _raw_df(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as fh:
            fh.write(SAMPLE_STATEMENT_CSV)
            path = fh.name
        try:
            return read_statement(path)
        finally:
            os.unlink(path)

    def test_filter_only_step(self):
        df = self._raw_df()
        p = Pipeline(steps=["filter"])
        result = p.run(df)
        assert set(result["Transaction Type"].unique()) == {"Advanced Trade Buy", "Buy"}

    def test_transform_only_step(self):
        df = self._raw_df()
        p = Pipeline(steps=["transform"])
        result = p.run(df)
        assert result["Total (inclusive of fees and/or spread)"].dtype == float

    def test_filter_then_transform(self):
        df = self._raw_df()
        p = Pipeline(steps=["filter", "transform"])
        result = p.run(df)
        assert set(result["Transaction Type"].unique()) == {"Advanced Trade Buy", "Buy"}
        assert result["Total (inclusive of fees and/or spread)"].dtype == float

    def test_all_steps(self, rates_csv):
        df = self._raw_df()
        src = FileCurrencySource(rates_csv)
        merger = CurrencyMerger(source=src)
        p = Pipeline(steps=ALL_STEPS, currency_merger=merger)
        result = p.run(df)
        assert "eur_pln_rate" in result.columns
        assert "total_pln" in result.columns
        assert set(result["Transaction Type"].unique()) == {"Advanced Trade Buy", "Buy"}

    def test_step_order_is_canonical(self):
        # Passing steps in wrong order still executes filter before transform
        p = Pipeline(steps=["transform", "filter"])
        assert p.steps == ["filter", "transform"]

    def test_unknown_step_raises(self):
        with pytest.raises(ValueError, match="Unknown pipeline steps"):
            Pipeline(steps=["nonexistent"])

    def test_merge_currency_without_merger_raises(self):
        with pytest.raises(ValueError, match="CurrencyMerger instance is required"):
            Pipeline(steps=["merge-currency"])

    def test_default_steps_are_all(self, rates_csv):
        src = FileCurrencySource(rates_csv)
        merger = CurrencyMerger(source=src)
        p = Pipeline(currency_merger=merger)
        assert p.steps == ALL_STEPS


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

class TestCLI:
    def _write_tmp(self, content, suffix=".csv"):
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "w") as fh:
            fh.write(content)
        return path

    def test_process_all_steps_with_file(self, tmp_path):
        stmt = self._write_tmp(SAMPLE_STATEMENT_CSV)
        rates = self._write_tmp(SAMPLE_RATES_CSV)
        output = str(tmp_path / "out.csv")
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "process",
                "--statement", stmt,
                "--currency-file", rates,
                "--output", output,
            ],
        )
        assert result.exit_code == 0, result.output
        out_df = pd.read_csv(output)
        assert "eur_pln_rate" in out_df.columns
        assert "total_pln" in out_df.columns
        os.unlink(stmt)
        os.unlink(rates)

    def test_process_filter_transform_only(self, tmp_path):
        stmt = self._write_tmp(SAMPLE_STATEMENT_CSV)
        output = str(tmp_path / "out.csv")
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "process",
                "--statement", stmt,
                "--steps", "filter,transform",
                "--output", output,
            ],
        )
        assert result.exit_code == 0, result.output
        out_df = pd.read_csv(output)
        assert set(out_df["Transaction Type"].unique()) == {"Advanced Trade Buy", "Buy"}
        assert "eur_pln_rate" not in out_df.columns
        os.unlink(stmt)

    def test_mutually_exclusive_currency_options(self, tmp_path):
        stmt = self._write_tmp(SAMPLE_STATEMENT_CSV)
        rates = self._write_tmp(SAMPLE_RATES_CSV)
        output = str(tmp_path / "out.csv")
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "process",
                "--statement", stmt,
                "--currency-file", rates,
                "--currency-api",
                "--output", output,
            ],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output
        os.unlink(stmt)
        os.unlink(rates)

    def test_merge_currency_requires_source(self, tmp_path):
        stmt = self._write_tmp(SAMPLE_STATEMENT_CSV)
        output = str(tmp_path / "out.csv")
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "process",
                "--statement", stmt,
                "--steps", "merge-currency",
                "--output", output,
            ],
        )
        assert result.exit_code != 0
        assert "currency-file" in result.output or "currency-api" in result.output
        os.unlink(stmt)
