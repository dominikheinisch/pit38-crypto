from __future__ import annotations

import datetime
import logging
from typing import Protocol

import pandas as pd
import requests

logger = logging.getLogger(__name__)

TIMESTAMP_COL = "Timestamp"
RATE_DATE_COL = "date"
RATE_COL = "rate"
OUTPUT_RATE_COL = "eur_pln_rate"
OUTPUT_CURRENCY_DATE_COL = "currency_date"
OUTPUT_TOTAL_PLN_COL = "total_pln"
TOTAL_COL = "Total (inclusive of fees and/or spread)"

NBP_BASE_URL = "https://api.nbp.pl/api/exchangerates/rates/A"


def _parse_rates_df(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[["date", "rate"]].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["rate"] = df["rate"].astype(float)
    return df.sort_values("date").reset_index(drop=True)


class CurrencySource(Protocol):
    def get_rates(self, currency: str, years: list[int]) -> pd.DataFrame: ...


class FileCurrencySource:
    """Load NBP rates from a CSV file (columns: ``currency_code, no, date, rate``)."""

    def __init__(self, path: str) -> None:
        self.path = path

    def get_rates(self, currency: str, years: list[int]) -> pd.DataFrame:
        df = _parse_rates_df(pd.read_csv(self.path))
        if years:
            min_year = min(years)
            in_years = df["date"].apply(lambda d: d.year).isin(years)
            # Dec 29–31 of the previous year cover Jan 1 transactions whose
            # previous working day falls in the prior year.
            prev_dec_tail = df["date"].apply(
                lambda d: d.year == min_year - 1 and d.month == 12 and d.day >= 29
            )
            df = df[in_years | prev_dec_tail]
        return df.reset_index(drop=True)


class NBPApiCurrencySource:
    """Fetch NBP exchange rates from the public API, one request per year.

    Each request covers ``{year-1}-12-29`` to ``{year}-12-30`` so that
    Jan 1 transactions can always resolve a rate from the prior December.
    """

    def get_rates(self, currency: str, years: list[int]) -> pd.DataFrame:
        frames = [self._fetch_year(currency.upper(), y) for y in sorted(set(years))]
        if not frames:
            return pd.DataFrame(columns=[RATE_DATE_COL, RATE_COL])
        combined = pd.concat(frames, ignore_index=True)
        # Adjacent year ranges overlap by 2 days (Dec 29–30); deduplicate.
        return (
            combined.drop_duplicates(subset=[RATE_DATE_COL])
            .sort_values(RATE_DATE_COL)
            .reset_index(drop=True)
        )

    def _fetch_year(self, currency: str, year: int) -> pd.DataFrame:
        url = f"{NBP_BASE_URL}/{currency}/{year - 1}-12-29/{year}-12-30/?format=json"
        logger.debug("Fetching NBP rates: %s", url)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        rows = [
            {"date": r["effectiveDate"], "rate": r["mid"]}
            for r in response.json()["rates"]
        ]
        return _parse_rates_df(pd.DataFrame(rows))


def _match_rate(
    rates_df: pd.DataFrame, txn_date: datetime.date
) -> tuple[float, datetime.date]:
    """Return ``(rate, rate_date)`` for the latest NBP date strictly before *txn_date*.

    Using strictly-less-than against NBP data (working days only) naturally
    covers weekends and public holidays without a calendar library.

    Raises:
        ValueError: When no rate exists before *txn_date*.
    """
    eligible = rates_df[rates_df[RATE_DATE_COL] < txn_date]
    if eligible.empty:
        raise ValueError(
            f"No exchange rate available before {txn_date}. "
            "Ensure the rates file/API covers the statement period."
        )
    best_idx = eligible[RATE_DATE_COL].idxmax()
    return (
        float(eligible.loc[best_idx, RATE_COL]),
        eligible.loc[best_idx, RATE_DATE_COL],
    )


class CurrencyMerger:
    """Attach NBP rate columns to a transformed statement DataFrame.

    Added columns:
    * ``eur_pln_rate``  — NBP mid-rate from the previous working day
    * ``currency_date`` — NBP publication date the rate was taken from
    * ``total_pln``     — ``Total (inclusive of fees and/or spread)`` × rate

    Args:
        source: A ``FileCurrencySource`` or ``NBPApiCurrencySource`` instance.
        currency: ISO currency code (default ``EUR``).
    """

    def __init__(
        self,
        source: FileCurrencySource | NBPApiCurrencySource,
        currency: str = "EUR",
    ) -> None:
        self.source = source
        self.currency = currency.upper()
        self._rates_cache: pd.DataFrame | None = None

    def _get_rates(self, years: list[int]) -> pd.DataFrame:
        if self._rates_cache is None:
            self._rates_cache = self.source.get_rates(self.currency, years)
        return self._rates_cache

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        years = sorted(df[TIMESTAMP_COL].dt.year.unique().tolist())
        rates = self._get_rates(years)

        matched = df[TIMESTAMP_COL].apply(lambda ts: _match_rate(rates, ts.date()))
        df[OUTPUT_RATE_COL] = matched.apply(lambda t: t[0])
        df[OUTPUT_CURRENCY_DATE_COL] = matched.apply(lambda t: t[1])
        df[OUTPUT_TOTAL_PLN_COL] = df[TOTAL_COL] * df[OUTPUT_RATE_COL]
        return df
