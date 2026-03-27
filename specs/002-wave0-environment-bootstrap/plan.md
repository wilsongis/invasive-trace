# Implementation Plan: Wave 0 - Environment Bootstrap

**Branch**: `002-wave0-environment-bootstrap` | **Date**: 2026-03-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-wave0-environment-bootstrap/spec.md`

**Note**: This plan defines the blocking bootstrap gate for all later waves. It is intentionally narrow: minimal runtime, database access path, migration baseline, and verified research grounding.

## Summary

Wave 0 establishes the minimum safe execution environment for Invasive Trace. The plan creates a minimal `app/` package, central runtime settings, an async SQLAlchemy/PostGIS access layer, an Alembic baseline, a DB smoke test, and verified NotebookLM grounding against the `gaia-atlas` Dev notebook. No business-domain endpoints, schema tables beyond migration scaffolding, or ML logic are introduced in this wave.

## Technical Context

**Language/Version**: Python 3.12 (managed by `uv`)
**Primary Dependencies**: FastAPI, SQLAlchemy (async) + GeoAlchemy2, Alembic, asyncpg, python-dotenv, pytest, pytest-asyncio
**Storage**: PostgreSQL 16 + PostGIS 3.4 — bootstrap only; canonical four-table schema lands in Wave 1
**Testing**: `pytest` + `pytest-asyncio` via `just test`
**Target Platform**: Podman-containerized Linux (macOS dev via `just run`)
**Project Type**: Geospatial AI web service
**Performance Goals**: `/healthz` responds in <= 250ms p95 locally (10-request sample); DB smoke test completes in <= 5s per run
**Constraints**: No business-domain endpoints; no schema drift; environment variables only; Podman + `just` only; `/api/v1` router present but bootstrap-scoped
**Scale/Scope**: Single local developer environment; one app service + one PostGIS service; one verified Dev NotebookLM connection

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify ALL of the following before proceeding:

- [x] **Anti-Context Rot (II)**: Checked `AGENTS.md` Sections 4, 5, 6 — no schema column names, API URLs, or model versions guessed.
- [x] **Tech Stack (III)**: Plan uses only mandated stack (FastAPI, uv, PostGIS, SQLAlchemy async, Alembic, Ruff, Podman, just). No prohibited tech introduced.
- [x] **Spatial Integrity (IV)**: Wave 0 introduces only migration scaffolding; canonical schema remains untouched until Wave 1 migration work.
- [x] **API Resilience (V)**: External API behavior is limited to NotebookLM connection verification; no remote-sensing or seeding consumers are implemented in this wave.
- [x] **ML Registry (VI)**: No model code is introduced; registry remains unchanged.

*Conclusion: GATE PASSED. Wave 0 is constitutionally compliant and may proceed to implementation.*

## Project Structure

### Documentation (this feature)

```text
specs/002-wave0-environment-bootstrap/
├── plan.md              # This file
├── research.md          # Technical decisions for bootstrap scope
├── data-model.md        # Bootstrap runtime entities
└── quickstart.md        # Wave 0 validation workflow
```

### Source Code (repository root)

```text
app/
├── __init__.py
├── main.py              # FastAPI app, lifespan, /healthz, bootstrap router include
├── config.py            # Environment-backed settings
├── db.py                # Async engine, session factory, get_db dependency
├── api/
│   ├── __init__.py
│   └── v1/
│       └── __init__.py  # Bootstrap router wiring only
├── models/__init__.py
├── services/__init__.py
├── ml/__init__.py
└── scripts/__init__.py

tests/
├── integration/
│   └── test_db_connection.py
└── unit/

migrations/
├── env.py
└── versions/

alembic.ini
```

**Structure Decision**: Wave 0 touches only bootstrap runtime files: `app/main.py`, `app/config.py`, `app/db.py`, `app/api/v1/__init__.py`, Alembic config, and a single DB integration smoke test. It deliberately does not create feature routers, ORM table models, or service implementations beyond the DB/session path.

## Implementation Phases

### Phase 0 — Runtime Skeleton

- Create the `app/` package tree and module placeholders.
- Add a minimal FastAPI app with lifespan hooks and `/healthz`.
- Include an empty bootstrap router under `/api/v1` to establish versioned API shape without exposing domain endpoints.

### Phase 1 — Configuration and DB Access

- Add a centralized settings module reading `DATABASE_URL`, `INAT_API_KEY`, `EDDMAPS_API_KEY`, `PC_SDK_SUBSCRIPTION_KEY`, and `LOG_LEVEL`.
- Create async SQLAlchemy engine/session setup and `get_db` dependency.
- Ensure startup/shutdown behavior is safe when DB is unavailable.

### Phase 2 — Migration Baseline

- Initialize Alembic under `migrations/`.
- Configure `alembic.ini` and `migrations/env.py` to resolve the DB URL from runtime settings.
- Establish a baseline revision with no canonical tables yet, only migration plumbing.

### Phase 3 — Verification Gate

- Add `tests/integration/test_db_connection.py` to query `pg_stat_activity` through the async session.
- Validate `just start`, `just db-migrate`, and `just verify` (with `just lint` / `just test` as diagnostics if verify fails).
- Verify NotebookLM connection with `just research-sync` and `just research-test`; upload `/docs/research/` manually via NotebookLM UI.
- Capture evidence for SC-004 in `specs/002-wave0-environment-bootstrap/checklists/requirements.md` after each completion attempt.

## Risk Management

| Risk | Mitigation |
| :--- | :--- |
| App boots but DB layer silently misconfigures | Fail fast from settings validation and exercise the async path in an integration test |
| Alembic uses stale or hard-coded connection settings | Resolve DB URL from the same runtime settings module used by the app |
| Wave 0 grows into domain work | Explicitly prohibit business endpoints and canonical schema implementation in this plan |
| NotebookLM is “connected” but research is not actually grounded | Require both MCP verification and manual upload of `/docs/research/` before Wave 0 completion |

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :-------- | :--------- | :---------------------------------- |
| None | N/A | N/A |
