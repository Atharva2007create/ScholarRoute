# ScholarRoute

ScholarRoute is a structured college and scholarship recommendation platform for Indian students. The product will use official, versioned data and deterministic eligibility rules. AI will never decide admission or scholarship eligibility.

Phase 8 adds an optional, grounded Gemini explanation layer. See
[`docs/phase-8-ai-explanations.md`](docs/phase-8-ai-explanations.md) for its server-only
configuration, safety boundaries, and local validation steps.

## Current phase

Phase 6 exposes the canonical reference catalog, Phase 4 eligibility, and Phase 5 recommendations
through a typed, versioned FastAPI REST layer. Frontend work, Gemini, and AI-based scoring remain
out of scope. See [`docs/api-v1.md`](docs/api-v1.md) for the endpoint contract.

## Architecture

The backend is a modular FastAPI monolith with a separately executable ingestion worker boundary. PostgreSQL is the authoritative data store. The initial schema keeps reference catalog, admission-cycle, release, and source-provenance concepts normalized and versioned. See [`docs/architecture.md`](docs/architecture.md) for the complete blueprint.

```text
apps/api/                         API container definition
apps/web/                         reserved Next.js application boundary
backend/scholarroute/             Python package
  application/                    use-case orchestration boundary
  domain/                         deterministic domain boundary
  entrypoints/api/                FastAPI app, routes, middleware, errors
  entrypoints/worker/             future ingestion-worker boundary
  infrastructure/db/              SQLAlchemy models and sessions
backend/migrations/               Alembic environment and migrations
backend/tests/                    unit and PostgreSQL integration tests
data-contracts/                   future source mappings and vocabularies
docs/                             architecture and engineering decisions
infra/                            future deployment definitions
packages/                         future generated contracts and shared UI
scripts/                          local database initialization
```

## Prerequisites

- Python 3.12+
- Docker Desktop with Docker Compose, or a local PostgreSQL 17 instance

Examples below use PowerShell from the repository root.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

`.env` is ignored by Git. Change local credentials there if necessary and use a secrets manager in deployed environments.

## Local PostgreSQL

```powershell
docker compose up -d postgres
docker compose ps
```

The first container initialization creates both `scholarroute` and `scholarroute_test`. If the named volume already exists from an older configuration, create the test database manually or recreate only this project's development volume.

Stop the service without deleting its data:

```powershell
docker compose down
```

## Migrations

```powershell
alembic upgrade head
alembic current
```

Create a reviewed migration after model changes:

```powershell
alembic revision --autogenerate -m "describe the change"
```

Do not use application startup to apply production migrations.

## Run the API

```powershell
uvicorn scholarroute.entrypoints.api.app:app --app-dir backend --reload
```

- Liveness: `GET http://127.0.0.1:8000/health`
- Readiness with PostgreSQL check: `GET http://127.0.0.1:8000/api/v1/health`
- OpenAPI: `GET http://127.0.0.1:8000/openapi.json`

## Quality checks

```powershell
ruff format --check backend
ruff check backend
mypy backend/scholarroute
pytest
```

Integration tests refuse to run against a database whose name does not end in `_test`. Override the isolated database only when needed:

```powershell
$env:SCHOLARROUTE_TEST_DATABASE_URL = "postgresql+psycopg://scholarroute:scholarroute@localhost:5432/scholarroute_test"
pytest -m integration
```

## Configuration

| Variable | Purpose | Local default/example |
|---|---|---|
| `SCHOLARROUTE_ENVIRONMENT` | `development`, `testing`, or `production` | `development` |
| `SCHOLARROUTE_LOG_LEVEL` | Python log level | `INFO` |
| `SCHOLARROUTE_DATABASE_URL` | SQLAlchemy PostgreSQL URL | local `scholarroute` database |
| `SCHOLARROUTE_DATABASE_POOL_SIZE` | Persistent connection-pool size | `5` |
| `SCHOLARROUTE_DATABASE_MAX_OVERFLOW` | Temporary connections above pool size | `10` |
| `SCHOLARROUTE_DATABASE_POOL_TIMEOUT_SECONDS` | Pool checkout timeout | `30` |
| `SCHOLARROUTE_DATABASE_CONNECT_TIMEOUT_SECONDS` | Initial PostgreSQL connection timeout | `5` |
| `SCHOLARROUTE_TEST_DATABASE_URL` | Isolated integration-test database | local `scholarroute_test` database |

## Baseline entities

The first migration creates the foundational catalog and provenance schema. Phase 3 adds
canonical admission, scholarship, official-link, provenance, and staged-record structures.
Phase 4 adds immutable eligibility input snapshots, evaluation audit records, per-rule traces,
official-link associations, and the admission fields required by typed eligibility predicates.
Phase 5 adds immutable ranking-profile versions, preference/profile snapshots, ranking runs, and
component-level recommendation audit records.

Run a bounded local structured-data import with:

    .\.venv\Scripts\python.exe -m scholarroute.application.ingestion josaa backend/tests/fixtures/josaa_2025_test.csv --year 2025 --source-url https://josaa.nic.in/test/2025.csv --title "JoSAA deterministic test fixture"

The Phase 3 ingestion entry point supports deterministic CSV, JSON, and XLSX input,
records source provenance and official links, rejects invalid records, and reuses an
existing run when the same source checksum is imported again. Repository fixtures
are clearly labeled test data and are not production catalog data.
