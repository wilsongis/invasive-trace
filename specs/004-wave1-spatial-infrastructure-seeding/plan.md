# Implementation Plan: Wave 1 - Pillar I Spatial Infrastructure & Seeding

**Branch**: `004-wave1-spatial-infrastructure-seeding` | **Date**: 2026-03-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-wave1-spatial-infrastructure-seeding/spec.md`

**Note**: This plan is limited to Pillar I spatial infrastructure and source seeding. It establishes the canonical schema, ROI API surface, and ground-truth ingestion paths required for later remote-sensing work, but it does not implement Wave 2 STAC querying or spectral ingestion.

## Summary

Wave 1 implements the four canonical PostGIS tables, exposes ROI CRUD-lite endpoints for create/list/fetch, and adds resilient iNaturalist and EDDMapS ingestion paths that can run from both a CLI entry point and an ROI-scoped sync endpoint. The migration and ORM work must match `AGENTS.md` Section 4 exactly so later Waves can build on a stable spatial contract. Observation ingestion follows the constitution-mandated retry and log-and-skip behavior for HTTP 429 and other recoverable source failures.

## Technical Context

**Language/Version**: Python 3.12 (managed by `uv`)
**Primary Dependencies**: FastAPI, SQLAlchemy (async) + GeoAlchemy2, Alembic, asyncpg, Pydantic, httpx, pytest, pytest-asyncio
**Storage**: PostgreSQL 16 + PostGIS 3.4 — canonical tables `regions_of_interest`, `invasion_predictions`, `ground_truth_observations`, `spectral_time_series`
**Testing**: `pytest` + `pytest-asyncio` via `just test`
**Target Platform**: Podman-containerized Linux (macOS dev via `just run`)
**Project Type**: Geospatial AI web service
**Performance Goals**: ROI create/fetch is interactive in local validation; seeding workflow completes with a summary payload and recovers from HTTP 429 within the configured retry budget
**Constraints**: All geometries stored as SRID 4326; canonical schema must match `AGENTS.md` exactly; API keys from environment variables only; Planetary Computer and spectral ingestion remain out of scope for this feature
**Scale/Scope**: Local validation against one or more ROIs and enough source data to confirm at least one inserted observation row

## Constitution Check

*GATE: Must pass before implementation begins. Re-check after design finalization.*

Verify ALL of the following before proceeding:

- [x] **Feature Branch Preflight**: Work is executed on a feature branch named `004-wave1-spatial-infrastructure-seeding` (or another valid Spec Kit feature-branch pattern), not directly on `main`.
- [x] **Anti-Context Rot (II)**: Checked `AGENTS.md` Sections 4, 5, and 6; canonical schema, API URLs, and model lineage rules are referenced directly.
- [ ] **Research-First (I)**: Dev notebook grounding preflight must be executed via `just research-sync` and `just research-test` before implementation starts (tracked by `T003A`).
- [x] **Tech Stack (III)**: The plan uses only the mandated stack: FastAPI, `uv`, PostGIS, SQLAlchemy async, GeoAlchemy2, Alembic, `httpx`, and Ruff/pytest.
- [x] **Spatial Integrity (IV)**: A migration is planned for the four canonical tables; SRID 4326, CHECK constraints, GiST indexes, and tri-state semantics remain preserved.
- [x] **API Resilience (V)**: iNaturalist and EDDMapS consumers will implement exponential backoff (max 3 retries) and log-and-skip failure behavior.
- [x] **ML Registry (VI)**: No new model versions are introduced; the plan preserves the Stage 2 lineage rule in the schema.

*Conclusion: GATE READY FOR IMPLEMENTATION PLANNING. Wave 1 remains constitutionally compliant; execute the pending Research-First preflight (`T003A`) immediately before implementation begins.*

## Project Structure

### Documentation (this feature)

```text
specs/004-wave1-spatial-infrastructure-seeding/
├── spec.md              # Feature specification
├── plan.md              # This file
└── tasks.md             # Implementation task list
```

### Source Code (repository root)

```text
app/
├── api/v1/
│   ├── rois.py                # ROI create/list/fetch endpoints
│   └── observations.py        # ROI-scoped observation sync endpoint
├── models/
│   ├── roi.py                 # RegionOfInterest ORM model
│   ├── prediction.py          # InvasionPrediction ORM model
│   ├── observation.py         # GroundTruthObservation ORM model
│   └── spectral.py            # SpectralTimeSeries ORM model
├── schemas/
│   └── roi.py                 # WKT input + GeoJSON output schemas
├── services/
│   ├── inat_consumer.py       # iNaturalist ingestion client
│   └── eddmaps_consumer.py    # EDDMapS ingestion client
└── scripts/
    └── seed_observations.py   # CLI seeding entry point

tests/
├── integration/
│   └── test_roi_endpoints.py
└── unit/
    ├── test_roi_schemas.py
    ├── test_inat_consumer.py
    └── test_eddmaps_consumer.py

migrations/
└── versions/                  # Alembic migration for canonical tables
```

**Structure Decision**: Wave 1 adds ORM model files, ROI schemas, versioned API routers for ROIs and observation sync, resilient source consumers, and a CLI seed script. It extends the existing app layout without introducing new top-level directories or any Wave 2-specific services.

## Implementation Phases

### Phase 0 — Canonical Schema Modeling

- Implement SQLAlchemy ORM models for all four canonical tables.
- Ensure geometry types, indexes, checks, and foreign keys mirror `AGENTS.md` exactly.
- Prepare imports so Alembic can autogenerate the canonical migration.
- Define deterministic duplicate-handling for repeated source syncs to avoid ambiguous duplicate observation rows.

### Phase 1 — Migration and ROI Surface

- Generate and review the canonical Wave 1 migration.
- Apply the migration in the local PostGIS environment.
- Add ROI schemas and endpoints for create/list/fetch using WKT input and GeoJSON output.

### Phase 2 — Source Consumers and CLI Seeding

- Implement async iNaturalist and EDDMapS consumers with retry, log, and skip behavior.
- Normalize records into `ground_truth_observations`, preserving `raw_payload`.
- Add a CLI entry point used by `just seed-data`.

### Phase 3 — ROI-Scoped Sync Endpoint

- Add `POST /api/v1/observations/sync` that resolves an ROI, bounds source queries, and returns a summary payload.
- Ensure partial source failure still yields a structured response and preserves successful inserts.

## Risk Management

| Risk | Mitigation |
| :--- | :--- |
| Migration deviates from the canonical schema | Review autogeneration output against `AGENTS.md` Section 4 before applying |
| Geometry serialization mismatch between WKT input and GeoJSON output | Add unit and integration tests for ROI schema round-trip behavior |
| Source APIs rate limit or partially fail | Implement bounded retry plus log-and-skip behavior and summary accounting |
| Repeated syncs duplicate observations unpredictably | Define deterministic duplicate handling in the consumers before validation |
| Wave 2 work leaks into Wave 1 scope | Keep STAC, indices, and scene ingestion explicitly out of this plan |

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :-------- | :--------- | :---------------------------------- |
| None | N/A | N/A |
