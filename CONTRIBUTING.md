# Contributing to netlab-platform

## Setup

```bash
./scripts/dev-setup.sh
```

This checks for Python 3.12+, Node 20+, Docker, and Containerlab, creates a
virtualenv, installs the API requirements plus the local packages in editable
mode, and installs the web dependencies.

## Running locally

```bash
docker compose up --build
```

- Web UI: http://localhost:5173
- API: http://localhost:8000 (OpenAPI docs at http://localhost:8000/docs)

Containerlab runs on the host, not inside the API container: the API talks to
the `containerlab` binary and the Docker socket on the host. For real lab
deploys you need Docker + Containerlab installed on the machine running the
API. See docs/architecture.md.

## Tests

```bash
# Python (drivers, topology, API)
pytest packages/drivers/tests packages/topology/tests apps/api/tests

# Topology YAML validation (also runs in CI on every PR touching labs/)
python scripts/validate-topologies.py

# Frontend typecheck + build
cd apps/web && npm run typecheck && npm run build

# Playwright E2E (needs the app running)
cd apps/web && npx playwright test
```

## Pull requests

Every PR runs CI: ruff, mypy, pytest, frontend typecheck/build, topology
validation, and a 2-node FRR integration deploy. Keep PRs small and scoped
to one deliverable. New NOS drivers must include unit tests proving the
driver interface contract (see packages/drivers/tests/test_base.py).

## Rules that are not negotiable

- Never commit a proprietary NOS image, image URL, or license key. FRR and
  Linux images are public; Cisco/Arista/Juniper images are BYO only.
- Never commit secrets. Use `.env` (gitignored) and `.env.example` for keys.
- No shell injection: all Containerlab/Docker invocations use argument lists,
  never `shell=True` with interpolated strings.
- Every new lab under `labs/` must pass `scripts/validate-topologies.py`.
