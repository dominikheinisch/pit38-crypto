#!/usr/bin/env python3
"""PreToolUse(Bash) hook: keep Python commands inside the project .venv.

This project uses a plain virtualenv at .venv (no uv). Because the harness shell
does not persist activation between commands, every Python command must either
activate the venv inline or call the interpreter/tool by its .venv/bin path.
Otherwise a bare `python`/`pip`/`pytest` hits the system interpreter (no pandas/
click) or pollutes the global environment. Blocks those with exit code 2.

Run with system python3 (not the venv) so it stays cheap on every Bash call.
"""

import json
import sys

cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "").strip()

# Allow anything that activates the venv inline or calls tools via .venv/bin.
if "activate" in cmd or ".venv/bin/" in cmd:
    sys.exit(0)

# Hard-block installs that would touch the global environment.
global_installs = (
    "pip install",
    "pip3 install",
    "pip uninstall",
    "pip3 uninstall",
    "python -m pip",
    "python3 -m pip",
)
for bad in global_installs:
    if bad in cmd:
        print(
            f"Blocked '{bad}': it would touch the global environment.\n"
            "Use the project venv: '.venv/bin/pip install -e \".[dev]\"' "
            "(or 'source .venv/bin/activate && pip ...').",
            file=sys.stderr,
        )
        sys.exit(2)

# Block bare Python-ecosystem entrypoints that should run from the venv.
bare_prefixes = ("pip ", "pip3 ", "python ", "python3 ", "pytest ", "pit38-crypto ")
exact = {"pip", "pip3", "python", "python3", "pytest", "pit38-crypto"}
if cmd in exact or cmd.startswith(bare_prefixes):
    print(
        "Use the project venv: prefix with '.venv/bin/' "
        "(e.g. '.venv/bin/pytest', '.venv/bin/python', '.venv/bin/pit38-crypto') "
        "or run 'source .venv/bin/activate && ...' first.",
        file=sys.stderr,
    )
    sys.exit(2)

sys.exit(0)
