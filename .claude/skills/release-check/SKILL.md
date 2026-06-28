---
name: release-check
description: Run the full quality gate before a release. Use when preparing a release or checking if pit38-crypto is ready to tag.
---

This project uses pip + the local `.venv` (no uv). Run each step and report pass/fail:

1. `.venv/bin/pytest` — all tests must pass.
2. `pre-commit run --all-files` — Ruff lint + format must pass. Ruff runs via pre-commit,
   not from the venv, so there is no `.venv/bin/ruff`.
3. Read `version` from `pyproject.toml` and confirm it matches the intended release tag.
4. Confirm `README.md` usage examples still match the current `pit38-crypto` CLI options
   (`.venv/bin/pit38-crypto process --help`).

Fix and rerun any failing check before continuing. Do not tag if any step fails.
