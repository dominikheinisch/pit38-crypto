from __future__ import annotations

import pandas as pd


class NumericTransformer:
    """Strip a currency symbol prefix and cast affected columns to float64.

    Any column where at least one non-null value starts with the symbol
    (or ``-<symbol>``) is auto-detected and converted.

    Args:
        currency_symbol: Prefix to detect and strip. Defaults to ``€``.
    """

    def __init__(self, currency_symbol: str = "€") -> None:
        self.currency_symbol = currency_symbol

    def _detect_currency_columns(self, df: pd.DataFrame) -> list[str]:
        symbol = self.currency_symbol
        return [
            col
            for col in df.columns
            if (series := df[col].dropna().astype(str)).str.startswith(symbol).any()
            or series.str.startswith(f"-{symbol}").any()
        ]

    @staticmethod
    def _parse_value(value: str, symbol: str) -> float:
        text = str(value).strip()
        negative = text.startswith("-")
        text = text.lstrip("-").lstrip(symbol).replace(",", "")
        result = float(text)
        return -result if negative else result

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        symbol = self.currency_symbol
        for col in self._detect_currency_columns(df):
            df[col] = df[col].apply(
                lambda v: self._parse_value(v, symbol) if pd.notna(v) else float("nan")
            )
        return df
