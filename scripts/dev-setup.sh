#!/usr/bin/env bash
# Development setup for netlab-platform.
# Checks for Python 3.12+, Node 20+, Docker, and Containerlab; creates a venv;
# installs the API requirements and the local packages in editable mode;
# installs the web dependencies.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail() { echo "ERROR: $*" >&2; exit 1; }

command -v python3 >/dev/null || fail "python3 not found (need 3.12+)"
PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "Python $PYVER"

command -v node >/dev/null || fail "node not found (need 20+)"
echo "Node $(node --version)"

if ! command -v docker >/dev/null; then
  echo "WARNING: docker not found — the API can run, but labs cannot deploy here."
fi
if ! command -v containerlab >/dev/null; then
  echo "WARNING: containerlab not found — install from https://containerlab.dev/install/"
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r apps/api/requirements.txt
pip install -q -e packages/shared -e packages/topology -e packages/drivers
pip install -q pytest ruff mypy

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — fill in OAuth keys before use."
fi

cd apps/web
if [ ! -d node_modules ]; then
  npm ci
fi
npx playwright install --with-deps chromium 2>/dev/null || npx playwright install chromium || true

echo "Done. Start with: docker compose up --build"
