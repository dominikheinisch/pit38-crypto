from __future__ import annotations

import click
import pandas as pd

from pit38_crypto.currency import CurrencyMerger, FileCurrencySource, NBPApiCurrencySource
from pit38_crypto.pipeline import ALL_STEPS, STEP_MERGE_CURRENCY, Pipeline
from pit38_crypto.reader import read_statement


@click.group()
def main() -> None:
    """pit38-crypto — Polish PIT-38 tax helper for crypto transactions."""


@main.command()
@click.option(
    "--statement",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the Coinbase statement CSV file.",
)
@click.option(
    "--steps",
    default=",".join(ALL_STEPS),
    show_default=True,
    help="Comma-separated pipeline steps: filter, transform, merge-currency.",
)
@click.option(
    "--currency-file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Currency rates CSV produced by nbp_currency_to_csv.sh.",
)
@click.option(
    "--currency-api",
    is_flag=True,
    default=False,
    help="Fetch currency rates live from the NBP API.",
)
@click.option(
    "--currency",
    default="EUR",
    show_default=True,
    help="ISO currency code (used with --currency-api).",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(dir_okay=False),
    help="Path for the output CSV file.",
)
def process(
    statement: str,
    steps: str,
    currency_file: str | None,
    currency_api: bool,
    currency: str,
    output: str,
) -> None:
    step_list = [s.strip() for s in steps.split(",") if s.strip()]

    if currency_file and currency_api:
        raise click.UsageError("--currency-file and --currency-api are mutually exclusive.")

    merger: CurrencyMerger | None = None
    if STEP_MERGE_CURRENCY in step_list:
        if not currency_file and not currency_api:
            raise click.UsageError(
                "merge-currency step requires either --currency-file or --currency-api."
            )
        source = FileCurrencySource(currency_file) if currency_file else NBPApiCurrencySource()
        merger = CurrencyMerger(source=source, currency=currency)

    try:
        pipeline = Pipeline(steps=step_list, currency_merger=merger)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    click.echo(f"Reading statement: {statement}")
    df: pd.DataFrame = read_statement(statement)
    click.echo(f"  {len(df)} rows loaded")

    df = pipeline.run(df)
    click.echo(f"  {len(df)} rows after pipeline")

    df.to_csv(output, index=False)
    click.echo(f"Output written to: {output}")
