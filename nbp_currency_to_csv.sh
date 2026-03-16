#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <CURRENCY_CODE> <YEAR> [OUTPUT_FILE]"
  echo "Example: $0 EUR 2024"
  exit 1
fi

CURRENCY=$(echo "$1" | tr '[:upper:]' '[:lower:]')
YEAR=$2
START="${YEAR}-01-01"
END="${YEAR}-12-31"

OUTPUT=${3:-./data/currency/${CURRENCY}pln_${YEAR}.csv}

URL="https://api.nbp.pl/api/exchangerates/rates/A/${CURRENCY}/${START}/${END}/?format=json"

echo "Fetching ${CURRENCY} rates for ${YEAR}..."

TMP=$(mktemp)

curl -s "$URL" > "$TMP"

# create directory if missing
mkdir -p "$(dirname "$OUTPUT")"

# write csv header
echo "currency_code,no,date,rate" > "$OUTPUT"

jq -r --arg code "$CURRENCY" '
  .rates[]
  | [$code, .no, .effectiveDate, .mid]
  | @csv
' "$TMP" >> "$OUTPUT"

rm "$TMP"

echo "Saved to $OUTPUT"
