"""Shared fixtures for the test suite."""

import datetime
from io import StringIO

import pandas as pd
import pytest


SAMPLE_STATEMENT_CSV = """\
,,,,,,,,,,
Transactions,,,,,,,,,,
User,User-1,abcdefgh-123456,,,,,,,,
ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes
15,2025-01-13 12:20:53 UTC,Advanced Trade Buy,ETH,0.00000302,EUR,€2279.00,€0.00688,€0.00692,€0.00004129548,Bought ETH
14,2025-01-11 11:59:44 UTC,Advanced Trade Buy,ETH,0.03232528,EUR,€2544.75,€82.25976,€83.24687,€0.98711707536,Bought ETH
10,2025-01-08 17:38:52 UTC,Advanced Trade Buy,ETH,0.01938143,EUR,€2600.68,€50.40490,€50.58131,€0.1764171408034,Bought ETH
8,2025-01-08 17:38:49 UTC,Retail Staking Transfer,SOL,0.124,EUR,€133.07,€16.500986,€16.500986,€0.00,
7,2025-01-08 09:53:22 UTC,Deposit,EUR,10,EUR,€1.00,€10.00,€10.00,€0.00,Deposit
5,2025-01-08 00:29:50 UTC,Advanced Trade Buy,ETH,0.00222173,EUR,€3416.08,€7.58961,€7.63515,€0.0455376445104,Bought ETH
4,2025-01-07 07:02:26 UTC,Advanced Trade Buy,BTC,0.000696305,EUR,€78900.81,€54.939029,€55.131315,€0.192286599774675,Bought BTC
3,2025-01-07 07:00:52 UTC,Advanced Trade Buy,BTC,0.002,EUR,€37730.45,€75.46090,€76.06459,€0.6036872,Bought BTC
2,2025-01-06 19:31:25 UTC,Advanced Trade Buy,BTC,0.00024294,EUR,€82576.94,€20.06124,€20.18161,€0.1203674508216,Bought BTC
1,2025-01-05 15:19:52 UTC,Buy,BTC,0.00012822,EUR,€36882.22,€4.72904,€5.00,€0.270961,Bought BTC
"""

SAMPLE_RATES_CSV = """\
currency_code,no,date,rate
eur,P90/A/NBP/2024,2024-12-27,4.2810
eur,P91/A/NBP/2024,2024-12-30,4.2890
eur,P92/A/NBP/2024,2024-12-31,4.2950
eur,001/A/NBP/2025,2025-01-02,4.2668
eur,002/A/NBP/2025,2025-01-03,4.2718
eur,003/A/NBP/2025,2025-01-07,4.2515
eur,004/A/NBP/2025,2025-01-08,4.2656
eur,005/A/NBP/2025,2025-01-09,4.2794
eur,006/A/NBP/2025,2025-01-10,4.2657
eur,007/A/NBP/2025,2025-01-13,4.2715
eur,008/A/NBP/2025,2025-01-14,4.2737
eur,009/A/NBP/2025,2025-01-15,4.2611
"""


@pytest.fixture()
def statement_csv(tmp_path):
    """Write the sample statement CSV to a temp file and return its path."""
    path = tmp_path / "statement.csv"
    path.write_text(SAMPLE_STATEMENT_CSV)
    return str(path)


@pytest.fixture()
def rates_csv(tmp_path):
    """Write the sample rates CSV to a temp file and return its path."""
    path = tmp_path / "eurpln.csv"
    path.write_text(SAMPLE_RATES_CSV)
    return str(path)


@pytest.fixture()
def raw_statement_df():
    """Raw (un-filtered, un-transformed) statement DataFrame."""
    from pit38_crypto.reader import read_statement

    buf = StringIO(SAMPLE_STATEMENT_CSV)
    # read_statement expects a file path; write to tmp and reload
    import tempfile, os

    fd, path = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(SAMPLE_STATEMENT_CSV)
        return read_statement(path)
    finally:
        os.unlink(path)


@pytest.fixture()
def rates_df():
    """Parsed rates DataFrame with date and rate columns."""
    from pit38_crypto.currency import _parse_rates_df

    raw = pd.read_csv(StringIO(SAMPLE_RATES_CSV))
    return _parse_rates_df(raw)
