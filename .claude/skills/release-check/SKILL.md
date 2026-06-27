---
name: release-check
description: Run the full quality gate before a release. Use when preparing a release or checking if pit38-crypto is ready to tag.
---

This project uses pip + the local `.venv` (no uv). Run each step and report pass/fail:

1. `.venv/bin/pytest` — all tests must pass.
2. `.venv/bin/ruff check .` — no lint errors.
3. `.venv/bin/ruff format --check .` — already formatted.
4. Read `version` from `pyproject.toml` and confirm it matches the intended release tag.
5. Confirm `README.md` usage examples still match the current `pit38-crypto` CLI options
   (`.venv/bin/pit38-crypto process --help`).

Fix and rerun any failing check before continuing. Do not tag if any step fails.
