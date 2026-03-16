from __future__ import annotations

import pandas as pd

from pit38_crypto.currency import CurrencyMerger
from pit38_crypto.filter import TransactionFilter
from pit38_crypto.transform import NumericTransformer

STEP_FILTER = "filter"
STEP_TRANSFORM = "transform"
STEP_MERGE_CURRENCY = "merge-currency"

ALL_STEPS = [STEP_FILTER, STEP_TRANSFORM, STEP_MERGE_CURRENCY]


class Pipeline:
    """Compose and run a subset of processing steps in canonical order.

    Args:
        steps: Any subset of ``["filter", "transform", "merge-currency"]``.
               Always executes in that fixed order regardless of list order.
               Defaults to all three.
        transaction_filter: Defaults to ``TransactionFilter()`` (buy-only).
        numeric_transformer: Defaults to ``NumericTransformer()`` (€ symbol).
        currency_merger: Required when ``"merge-currency"`` is in *steps*.
    """

    def __init__(
        self,
        steps: list[str] | None = None,
        *,
        transaction_filter: TransactionFilter | None = None,
        numeric_transformer: NumericTransformer | None = None,
        currency_merger: CurrencyMerger | None = None,
    ) -> None:
        requested = set(steps) if steps is not None else set(ALL_STEPS)
        unknown = requested - set(ALL_STEPS)
        if unknown:
            raise ValueError(f"Unknown pipeline steps: {sorted(unknown)}")

        if STEP_MERGE_CURRENCY in requested and currency_merger is None:
            raise ValueError(
                "A CurrencyMerger instance is required when "
                "'merge-currency' is included in the pipeline steps."
            )

        self.steps = [s for s in ALL_STEPS if s in requested]
        self._filter = transaction_filter or TransactionFilter()
        self._transform = numeric_transformer or NumericTransformer()
        self._merger = currency_merger

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        for step in self.steps:
            if step == STEP_FILTER:
                df = self._filter.apply(df)
            elif step == STEP_TRANSFORM:
                df = self._transform.apply(df)
            elif step == STEP_MERGE_CURRENCY:
                df = self._merger.apply(df)
        return df
