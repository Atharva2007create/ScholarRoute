# Production data ingestion

The production pipeline is manifest-driven and keeps downloaded snapshots and
prepared payloads outside Git (`data/production/raw/` and
`data/production/prepared/`). The checked-in manifest is
`data/production/manifest.json`; every published row retains source authority,
document version, checksum, official URL, and source locator evidence.

Run the stages from the repository root with the existing `.venv`:

```powershell
.venv\Scripts\python -m scholarroute.application.ingestion.production_cli discover
.venv\Scripts\python -m scholarroute.application.ingestion.production_cli fetch
.venv\Scripts\python -m scholarroute.application.ingestion.production_cli parse
.venv\Scripts\python -m scholarroute.application.ingestion.production_cli validate
.venv\Scripts\python -m scholarroute.application.ingestion.production_cli stage
.venv\Scripts\python -m scholarroute.application.ingestion.production_cli promote
.venv\Scripts\python -m scholarroute.application.ingestion.production_cli coverage
```

`stage` is review-only and does not publish canonical rows. `promote` is
transactional and idempotent by source checksum/run. The pipeline never
fabricates an official URL; a source must provide one or validation rejects the
record. `docs/production-data-coverage.md` is the generated coverage report.

The PM-USP CSSS FAQ is retained in the manifest as `BLOCKED` because the
official Ministry URL currently returns 404. When the Ministry republishes it,
download the exact PDF into the ignored raw directory, update only the manifest
retrieval metadata, and rerun parse → validate → stage → promote.
