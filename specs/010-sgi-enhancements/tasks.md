# SGI Way Enhancements – Implementation Tasks

The following tasks are organized by SGI pillar.  Each task follows the standard checklist format used throughout the repository.

## Phase 0 – Foundations

- [ ] T001 Create `restoration_protocols` table migration (SQLAlchemy + Alembic)
- [ ] T002 Add API router `app/api/v1/protocols.py` with CRUD endpoints
- [ ] T003 Add `project_metrics` table migration for KPI storage
- [ ] T004 Add `/api/v1/metrics` endpoint returning KPI JSON
- [ ] T005 Extend `app/config.py` with `MAX_CONCURRENT_JOBS`, `TILE_SIZE`, and `RANDOM_SEED` settings

## Phase 1 – Standardized & Provable

- [ ] T006 Implement service layer `app/services/protocol_service.py` for protocol management
- [ ] T007 Implement service `app/services/metrics_service.py` to compute and store KPIs after each project run
- [ ] T008 Write unit tests for protocol CRUD and metrics endpoint

## Phase 2 – Repeatable & Efficient

- [ ] T009 Create deterministic pipeline wrapper `app/services/deterministic_runner.py` (sets seed, logs provenance)
- [ ] T010 Add provenance logger `app/services/provenance_logger.py` (model version, hyper‑params, input hash)
- [ ] T011 Refactor existing ML pipelines to use the deterministic runner
- [ ] T012 Implement async job queue using `asyncio.Semaphore` respecting `MAX_CONCURRENT_JOBS`
- [ ] T013 Add UI shortcuts in `app/templates/dashboard.html` for common actions (e.g., bulk ROI upload)

## Phase 3 – Scalable

- [ ] T014 Add spatial tiling utility `app/services/tiling.py` (configurable tile size)
- [ ] T015 Modify scene ingestion pipeline to process tiles independently
- [ ] T016 Update `compose.yml` to expose multiple FastAPI replicas behind a load balancer (e.g., Traefik)
- [ ] T017 Add integration tests for tiled processing and load‑balanced deployment

## Phase 4 – Innovative

- [ ] T018 Create plug‑in framework skeleton `app/plugins/__init__.py` and loader `app/plugins/loader.py`
- [ ] T019 Add sandbox endpoint `app/api/v1/sandbox.py` to execute a selected plug‑in on supplied data
- [ ] T020 Write a dummy plug‑in `app/plugins/example_plugin.py` that returns a static prediction
- [ ] T021 Add tests for plug‑in discovery and sandbox execution

## Phase 5 – GEDI Integration (Provable + Innovative)

- [ ] T025 [P] Create `gedi_observations` table migration in `migrations/versions/0005_gedi_observations.py`
- [ ] T026 [P] Add SQLAlchemy ORM model `app/models/gedi_observation.py` (footprint_id, acquisition_date, canopy_height, biomass, quality_flag, geom)
- [ ] T027 Implement GEDI client `app/services/gedi_client.py` — Earthdata auth, Level‑2A HDF5 fetch, and parse to records
- [ ] T028 Implement GEDI ingestion script `app/scripts/ingest_gedi.py` — reads HDF5 files, upserts into `gedi_observations`
- [ ] T029 Add Pydantic schemas `app/schemas/gedi.py` (GEDIRecord, GEDIIngestRequest, GEDIIngestResponse)
- [ ] T030 Add API endpoint `app/api/v1/gedi.py` — `POST /api/v1/gedi/ingest` and `GET /api/v1/gedi/observations`
- [ ] T031 Extend `/api/v1/metrics` to include GEDI‑derived KPIs (avg canopy height change, biomass delta per ROI)
- [ ] T032 [P] Write unit tests for GEDI client parsing and schema validation in `tests/unit/test_gedi_client.py`
- [ ] T033 Write integration test `tests/integration/test_gedi_ingestion.py` covering upsert and metrics rollup
- [ ] T034 Update `AGENTS.md` Section 5 with GEDI API contract (Earthdata endpoint, auth, failure modes)
- [ ] T035 Update `docs/research/02-ARCHITECTURE.md` with GEDI data flow diagram notes

## Phase 6 – Documentation & Checklist

- [ ] T022 Update `docs/research/02-ARCHITECTURE.md` with SGI Way extensions (already added)
- [ ] T023 Create SGI checklist `specs/010-sgi-enhancements/checklists/requirements.md` using the unit‑test‑for‑requirements style
- [ ] T024 Review and approve all new API specs in `specs/010-sgi-enhancements/spec.md`

---
*Generated on 2026‑04‑23.*
