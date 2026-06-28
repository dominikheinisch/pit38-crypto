# pit38-crypto

Polish PIT-38 tax calculator for cryptocurrency transactions exported from Coinbase.
Small CLI app: read a Coinbase statement CSV, run a processing pipeline, write a CSV/XLSX with PLN values.

## Package management & environment

This project uses **pip + a local virtualenv at `.venv`**.
The harness shell does **not** persist venv activation between commands, so call tools by
their venv path every time:

- Run code/tools: `.venv/bin/python ...`, `.venv/bin/pytest`, `.venv/bin/pit38-crypto ...`
- Install deps:   `.venv/bin/pip install -e ".[dev]"`
- Never use a bare `python` / `pip` / `pytest` (that hits the system interpreter, which lacks
  pandas/click) and never `pip install` into the global environment.

Dependencies are declared in `pyproject.toml` (`dependencies` + the `dev` extra under
`[project.optional-dependencies]`). Edit them there, then `.venv/bin/pip install -e ".[dev]"`
to apply.

## Testing

`.venv/bin/pytest` — 54 tests, runs in well under a second. Tests live in `tests/`,
src-layout imports (`from pit38_crypto.currency import ...`). Shared sample CSV fixtures
(`statement_csv`, `rates_csv`, `raw_statement_df`, `rates_df`) are in `tests/conftest.py`;
reuse them rather than inlining new sample data.

## Code style

**Ruff is the linter and formatter**, run via pre-commit only — it is *not* a project
dependency and there is no per-edit hook, so `.venv/bin/ruff` does not exist. A committed
`.pre-commit-config.yaml` (managed `astral-sh/ruff-pre-commit`, pinned by `rev`) runs
`ruff check --fix` + `ruff format` on every `git commit`. Config lives in `pyproject.toml`
under `[tool.ruff]`. No type checker is wired up.

- Activate the hook once per clone: `pre-commit install`
- Run Ruff on demand (all files):  `pre-commit run --all-files`

Rules: `E, F, I, UP, B`; `tests/*` relaxes `E501`/`E731` (long CSV fixtures, lambda rule
callables). Beyond what Ruff enforces, follow these by hand:

- `from __future__ import annotations` at the top of modules using `X | None` annotations.
- Full type hints on public functions/methods; keyword-only args after `*` where the code does.
- Module-level UPPER_CASE constants for column names / magic strings (see `currency.py`,
  `reader.py`) — reuse these constants, don't hardcode the literal strings again.
- Docstrings on public classes/functions (Google-style `Args:`/`Raises:`), with short
  `#` comments explaining non-obvious domain rules.
- **Comment only what's essential.** Write a comment when it adds something the code can't
  say on its own — the *why*, a domain rule, a non-obvious edge case or workaround. Skip
  comments that just restate the code (`# increment i`, `# loop over rows`, `# return result`).
  When in doubt, prefer clearer names/structure over a comment. This applies to all code Claude
  writes in this repo.
- pandas: operate on a `df.copy()` in `apply()` methods; never mutate the caller's DataFrame.

## Architecture

`src/pit38_crypto/`:
- `cli.py` — `click` group; `process` command wires options into a `Pipeline`.
- `pipeline.py` — `Pipeline` runs a subset of steps in **fixed canonical order**
  (`filter` → `transform` → `merge-currency`) regardless of input order.
- `reader.py` — `read_statement()`; Coinbase exports have 3 metadata rows before the header
  (`STATEMENT_SKIPROWS = 3`); `Timestamp` is parsed UTC.
- `filter.py` — `TransactionFilter`, buy-only by default (`Advanced Trade Buy`, `Buy`).
- `transform.py` — `NumericTransformer` strips a `€` prefix and casts columns to float64.
- `currency.py` — `CurrencyMerger` + two `CurrencySource`s (`FileCurrencySource`,
  `NBPApiCurrencySource`) attach NBP EUR/PLN rates.

## Domain rules (get these wrong and the tax math is wrong)

- The applicable rate is the NBP mid-rate of the **previous working day** before the
  transaction date — implemented as the latest NBP date **strictly less than** the txn date
  (`_match_rate`). NBP only publishes on working days, so `<` naturally skips weekends/holidays.
- **Turn of the year:** a Jan 1–2 transaction needs a rate from the prior December. Both the
  file source and the API source deliberately include the previous year's late-December dates
  (Dec 29–31). Preserve this when touching `currency.py`.
- NBP API: one request per year covering `{year-1}-12-29 .. {year}-12-30`; adjacent ranges
  overlap by 2 days and are de-duplicated. For the **in-progress year** the end is clamped to
  *today* (`NBPApiCurrencySource(today=...)`, defaults to `date.today()`) — NBP rejects any
  range reaching into the future with `400 Invalid date range`.

## Data & helper script

- `data/` is git-ignored. Layout: `data/statement/`, `data/currency/`, `data/results/`.
  Use the `*.sample.csv` files for examples/docs.
- `nbp_currency_to_csv.sh EUR 2025` fetches a year of NBP rates into a CSV (bash + curl + jq).

## Keep docs in sync

When you change tooling, commands, dependencies, or behavior, update the docs and Claude
config in the same change — keep `README.md`, this `CLAUDE.md`, `.claude/` (settings, hooks,
skills), and `pyproject.toml` consistent so they never drift from how the project actually works.
