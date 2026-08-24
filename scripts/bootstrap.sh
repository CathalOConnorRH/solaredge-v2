#!/usr/bin/env bash
#
# Create a local dev/test venv for the aiosolaredge-one library.
#
# Reproducible from a fresh clone on any machine. Creates ".venv" in the repo
# root (gitignored) with the library installed editable plus the dev tools
# (pytest, mypy, ruff).
#
# Usage:
#   scripts/bootstrap.sh
#
# Overrides (env vars):
#   PYTHON=python3.11         interpreter to build the venv from (3.11+; use 3.13
#                             if you also run the integration tests from here)
#   VENV=/path/to/.venv       where to create the venv
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${VENV:-$REPO_ROOT/.venv}"
PYTHON="${PYTHON:-python3.13}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "error: '$PYTHON' not found. This library needs Python 3.11+." >&2
  echo "       Install it or set PYTHON=... (e.g. PYTHON=python3.11)." >&2
  exit 1
fi

echo "==> Creating venv at $VENV ($($PYTHON --version))"
"$PYTHON" -m venv "$VENV"
PY="$VENV/bin/python"

echo "==> Upgrading pip"
"$PY" -m pip install --quiet --upgrade pip

echo "==> Installing aiosolaredge-one (editable) with dev extras"
"$PY" -m pip install --quiet -e "$REPO_ROOT[dev]"

echo
echo "Done. Run from the repo root:"
echo "  $VENV/bin/python -m pytest"
echo "  $VENV/bin/ruff check src tests"
echo "  $VENV/bin/mypy src"
