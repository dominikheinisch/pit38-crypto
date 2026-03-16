"""Tests for pit38_crypto.currency — previous-working-day logic and sources."""

import datetime
import json
import os
import tempfile
from io import StringIO

import pandas as pd
import pytest
import responses as responses_lib

from pit38_crypto.currency import (
    FileCurrencySource,
    NBPApiCurrencySource,
    CurrencyMerger,
    _match_rate,
    _parse_rates_df,
    NBP_BASE_URL,
    OUTPUT_CURRENCY_DATE_COL,
)
from tests.conftest import SAMPLE_RATES_CSV


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rates_df():
    raw = pd.read_csv(StringIO(SAMPLE_RATES_CSV))
    return _parse_rates_df(raw)


# ---------------------------------------------------------------------------
# _match_rate — previous-working-day logic
# ---------------------------------------------------------------------------

class TestMatchRate:
    """Verify the strictly-less-than date lookup."""

    def test_weekday_uses_previous_day(self):
        # 2025-01-08 is Wednesday; previous working day is Tuesday 2025-01-07
        rates = _rates_df()
        rate, date = _match_rate(rates, datetime.date(2025, 1, 8))
        assert rate == pytest.approx(4.2515)  # 2025-01-07 rate
        assert date == datetime.date(2025, 1, 7)

    def test_monday_uses_friday(self):
        # 2025-01-13 is Monday; prev working day is Friday 2025-01-10
        rates = _rates_df()
        rate, date = _match_rate(rates, datetime.date(2025, 1, 13))
        assert rate == pytest.approx(4.2657)  # 2025-01-10 rate
        assert date == datetime.date(2025, 1, 10)

    def test_tuesday_after_holiday(self):
        # 2025-01-07 is Tuesday; Mon Jan 6 = Epiphany (PL public holiday, no NBP rate)
        # so the latest date < Jan 7 in the table is Jan 3 (Friday)
        rates = _rates_df()
        rate, date = _match_rate(rates, datetime.date(2025, 1, 7))
        assert rate == pytest.approx(4.2718)  # 2025-01-03 rate
        assert date == datetime.date(2025, 1, 3)

    def test_sunday_uses_friday(self):
        # 2025-01-12 is Sunday; prev working day is Friday 2025-01-10
        rates = _rates_df()
        rate, date = _match_rate(rates, datetime.date(2025, 1, 12))
        assert rate == pytest.approx(4.2657)  # 2025-01-10 rate
        assert date == datetime.date(2025, 1, 10)

    def test_same_date_in_table_not_used(self):
        # Transaction on 2025-01-10 should use Jan 9, not Jan 10 itself
        rates = _rates_df()
        rate, date = _match_rate(rates, datetime.date(2025, 1, 10))
        assert rate == pytest.approx(4.2794)  # 2025-01-09 rate
        assert date == datetime.date(2025, 1, 9)

    def test_raises_when_no_prior_rate(self):
        rates = _rates_df()
        with pytest.raises(ValueError, match="No exchange rate available"):
            _match_rate(rates, datetime.date(2025, 1, 1))


# ---------------------------------------------------------------------------
# FileCurrencySource
# ---------------------------------------------------------------------------

class TestFileCurrencySource:
    def test_loads_rates(self, rates_csv):
        src = FileCurrencySource(rates_csv)
        df = src.get_rates("EUR", [2025])
        assert len(df) == 9
        assert list(df.columns) == ["date", "rate"]

    def test_date_type(self, rates_csv):
        src = FileCurrencySource(rates_csv)
        df = src.get_rates("EUR", [2025])
        assert isinstance(df.loc[0, "date"], datetime.date)

    def test_rate_type(self, rates_csv):
        src = FileCurrencySource(rates_csv)
        df = src.get_rates("EUR", [2025])
        assert df["rate"].dtype == float

    def test_empty_years_returns_all(self, rates_csv):
        src = FileCurrencySource(rates_csv)
        df = src.get_rates("EUR", [])
        # No year filter applied → all 9 rows returned
        assert len(df) == 9


# ---------------------------------------------------------------------------
# NBPApiCurrencySource
# ---------------------------------------------------------------------------

class TestNBPApiCurrencySource:
    @responses_lib.activate
    def test_fetches_and_parses(self):
        payload = {
            "table": "A",
            "currency": "euro",
            "code": "EUR",
            "rates": [
                {"no": "001/A/NBP/2025", "effectiveDate": "2025-01-02", "mid": 4.2668},
                {"no": "002/A/NBP/2025", "effectiveDate": "2025-01-03", "mid": 4.2718},
            ],
        }
        url = f"{NBP_BASE_URL}/EUR/2025-01-01/2025-12-31/?format=json"
        responses_lib.add(responses_lib.GET, url, json=payload, status=200)

        src = NBPApiCurrencySource()
        df = src.get_rates("EUR", [2025])
        assert len(df) == 2
        assert df.loc[0, "rate"] == pytest.approx(4.2668)
        assert df.loc[1, "date"] == datetime.date(2025, 1, 3)

    @responses_lib.activate
    def test_multi_year_concatenates(self):
        def _payload(year):
            return {
                "table": "A",
                "currency": "euro",
                "code": "EUR",
                "rates": [
                    {"no": f"001/A/NBP/{year}", "effectiveDate": f"{year}-01-02", "mid": 4.0},
                ],
            }

        for year in (2024, 2025):
            url = f"{NBP_BASE_URL}/EUR/{year}-01-01/{year}-12-31/?format=json"
            responses_lib.add(responses_lib.GET, url, json=_payload(year), status=200)

        src = NBPApiCurrencySource()
        df = src.get_rates("EUR", [2024, 2025])
        assert len(df) == 2


# ---------------------------------------------------------------------------
# CurrencyMerger
# ---------------------------------------------------------------------------

class TestCurrencyMerger:
    def _filtered_transformed_df(self):
        """Return a small buy-only, numerically-transformed DataFrame."""
        from pit38_crypto.filter import TransactionFilter
        from pit38_crypto.transform import NumericTransformer
        from pit38_crypto.reader import read_statement
        from tests.conftest import SAMPLE_STATEMENT_CSV
        import tempfile, os

        fd, path = tempfile.mkstemp(suffix=".csv")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(SAMPLE_STATEMENT_CSV)
            df = read_statement(path)
        finally:
            os.unlink(path)

        df = TransactionFilter().apply(df)
        df = NumericTransformer().apply(df)
        return df

    def test_adds_rate_column(self, rates_csv):
        df = self._filtered_transformed_df()
        src = FileCurrencySource(rates_csv)
        merger = CurrencyMerger(source=src)
        result = merger.apply(df)
        assert "eur_pln_rate" in result.columns

    def test_adds_currency_date_column(self, rates_csv):
        df = self._filtered_transformed_df()
        src = FileCurrencySource(rates_csv)
        merger = CurrencyMerger(source=src)
        result = merger.apply(df)
        assert OUTPUT_CURRENCY_DATE_COL in result.columns

    def test_currency_date_is_before_transaction(self, rates_csv):
        df = self._filtered_transformed_df()
        src = FileCurrencySource(rates_csv)
        merger = CurrencyMerger(source=src)
        result = merger.apply(df)
        for _, row in result.iterrows():
            assert row[OUTPUT_CURRENCY_DATE_COL] < row["Timestamp"].date()

    def test_adds_total_pln_column(self, rates_csv):
        df = self._filtered_transformed_df()
        src = FileCurrencySource(rates_csv)
        merger = CurrencyMerger(source=src)
        result = merger.apply(df)
        assert "total_pln" in result.columns

    def test_total_pln_calculation(self, rates_csv):
        df = self._filtered_transformed_df()
        src = FileCurrencySource(rates_csv)
        merger = CurrencyMerger(source=src)
        result = merger.apply(df)
        for _, row in result.iterrows():
            expected = row["Total (inclusive of fees and/or spread)"] * row["eur_pln_rate"]
            assert row["total_pln"] == pytest.approx(expected)

    def test_rate_is_previous_working_day(self, rates_csv):
        df = self._filtered_transformed_df()
        src = FileCurrencySource(rates_csv)
        merger = CurrencyMerger(source=src)
        result = merger.apply(df)
        # Row with Timestamp 2025-01-13 (Monday) should use rate from 2025-01-10 (Friday)
        jan13_row = result[result["Timestamp"].dt.date == datetime.date(2025, 1, 13)]
        assert not jan13_row.empty
        assert jan13_row.iloc[0]["eur_pln_rate"] == pytest.approx(4.2657)
        assert jan13_row.iloc[0][OUTPUT_CURRENCY_DATE_COL] == datetime.date(2025, 1, 10)

    def test_original_df_not_mutated(self, rates_csv):
        df = self._filtered_transformed_df()
        src = FileCurrencySource(rates_csv)
        merger = CurrencyMerger(source=src)
        merger.apply(df)
        assert "eur_pln_rate" not in df.columns
