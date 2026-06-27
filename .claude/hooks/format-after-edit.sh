#!/usr/bin/env bash
# PostToolUse(Write|Edit) hook: auto-format an edited Python file IF a formatter
# is present in the project venv. Dormant (no-op) until you add ruff or black to
# the dev dependencies. Never fails the edit (always exits 0).
#
# Requires jq.
f=$(cat | jq -r '.tool_input.file_path // empty')
[[ "$f" == *.py && -f "$f" ]] || exit 0

if [[ -x .venv/bin/ruff ]]; then
  .venv/bin/ruff check --fix --quiet "$f" 2>/dev/null
  .venv/bin/ruff format --quiet "$f" 2>/dev/null
elif [[ -x .venv/bin/black ]]; then
  .venv/bin/black --quiet "$f" 2>/dev/null
fi
exit 0
