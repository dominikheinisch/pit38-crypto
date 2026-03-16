# pit38-crypto

Polish PIT-38 tax calculator for cryptocurrency transactions exported from Coinbase.

## Features

- **Filter** — keep only purchase transactions (`Advanced Trade Buy`, `Buy`)
- **Transform** — auto-detect and convert `€`-prefixed columns to `float64`
- **Merge currency** — attach NBP EUR/PLN mid-rate (previous working day) via CSV file or live API

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### All steps, using a currency CSV file

```bash
pit38-crypto process \
  --statement data/statement/statement-2025.sample.csv \
  --currency-file data/currency/eurpln-2025.sample.csv \
  --output result.csv
```

### All steps, fetching rates live from the NBP API

```bash
pit38-crypto process \
  --statement data/statement/statement-2025.sample.csv \
  --currency-api \
  --currency EUR \
  --output result.csv
```

### Only filter and transform (no currency merge)

```bash
pit38-crypto process \
  --statement data/statement/statement-2025.sample.csv \
  --steps filter,transform \
  --output result.csv
```

### Generate a currency CSV file

```bash
bash nbp_currency_to_csv.sh EUR 2025
```

## Development

```bash
pip install -e ".[dev]"
pytest
```
