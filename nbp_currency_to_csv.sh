#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <CURRENCY_CODE> <YEAR> [OUTPUT_FILE]"
  echo "Example: $0 EUR 2024"
  exit 1
fi

CURRENCY=$(echo "$1" | tr '[:upper:]' '[:lower:]')
YEAR=$2
# Start from Dec 29 of the previous year so that Jan 1 transactions can
# always resolve a rate from the prior December (handles weekend/holiday edge cases).
START="$((YEAR - 1))-12-29"
END="${YEAR}-12-30"

OUTPUT=${3:-./data/currency/${CURRENCY}pln-${YEAR}.csv}

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
