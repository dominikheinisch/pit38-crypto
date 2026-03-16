from __future__ import annotations

from collections.abc import Callable

import pandas as pd

TRANSACTION_TYPE_COL = "Transaction Type"

_buy_rule: Callable[[pd.DataFrame], pd.Series] = lambda df: df[
    TRANSACTION_TYPE_COL
].isin(["Advanced Trade Buy", "Buy"])


class TransactionFilter:
    """Filter statement rows to those matching all given rules.

    Args:
        rules: Callables ``(df) -> BooleanSeries`` ANDed together.
               Defaults to buy-only (Advanced Trade Buy, Buy).
    """

    DEFAULT_RULES: list[Callable[[pd.DataFrame], pd.Series]] = [_buy_rule]

    def __init__(
        self,
        rules: list[Callable[[pd.DataFrame], pd.Series]] | None = None,
    ) -> None:
        self.rules = rules if rules is not None else list(self.DEFAULT_RULES)

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        mask = pd.Series(True, index=df.index)
        for rule in self.rules:
            mask = mask & rule(df)
        return df[mask].reset_index(drop=True)
