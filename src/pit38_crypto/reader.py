"""Coinbase statement CSV reader.

Coinbase exports have 3 metadata rows before the actual header:
  Line 1: empty (commas only)
  Line 2: "Transactions,..."
  Line 3: "User,<user-id>,..."
  Line 4: column headers (ID, Timestamp, ...)
"""

import pandas as pd

STATEMENT_SKIPROWS = 3
TIMESTAMP_COL = "Timestamp"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S UTC"


def read_statement(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, skiprows=STATEMENT_SKIPROWS)
    df[TIMESTAMP_COL] = pd.to_datetime(
        df[TIMESTAMP_COL], format=TIMESTAMP_FORMAT, utc=True
    )
    return df
