# SGI Way Enhancements – Implementation Tasks

The following tasks are organized by SGI pillar.  Each task follows the standard checklist format used throughout the repository.

## Phase 0 – Foundations

- [x] T001 Create `restoration_protocols` table migration (SQLAlchemy + Alembic)
- [x] T002 Add API router `app/api/v1/protocols.py` with CRUD endpoints
- [x] T003 Add `project_metrics` table migration for KPI storage
- [~] T004 Add `/api/v1/metrics` endpoint returning KPI JSON <!-- PARTIAL: metrics endpoint exists but returns mock data -->
- [x] T005 Extend `app/config.py` with `MAX_CONCURRENT_JOBS`, `TILE_SIZE`, and `RANDOM_SEED` settings

## Phase 1 – Standardized & Provable

- [x] T006 Implement service layer `app/services/protocol_service.py` for protocol management
- [~] T007 Implement service `app/services/metrics_service.py` to compute and store KPIs after each project run <!-- PARTIAL: metrics_service exists but calculate_kpi_for_roi returns mock data -->
- [ ] T008 Write unit tests for protocol CRUD and metrics endpoint

## Phase 2 – Repeatable & Efficient

- [x] T009 Create deterministic pipeline wrapper `app/services/deterministic_runner.py` (sets seed, logs provenance)
- [x] T010 Add provenance logger `app/services/provenance_logger.py` (model version, hyper‑params, input hash)
- [~] T011 Refactor existing ML pipelines to use the deterministic runner <!-- PARTIAL: deterministic_runner exists but not verified in ML pipelines -->
- [x] T012 Implement async job queue using `asyncio.Semaphore` respecting `MAX_CONCURRENT_JOBS`
- [~] T013 Add UI shortcuts in `app/templates/dashboard.html` for common actions (e.g., bulk ROI upload) <!-- PARTIAL: dashboard has some shortcuts but not SGI-specific -->

## Phase 3 – Scalable

- [x] T014 Add spatial tiling utility `app/services/tiling.py` (configurable tile size)
- [~] T015 Modify scene ingestion pipeline to process tiles independently <!-- PARTIAL: tiling.py exists but scene ingestion integration not verified -->
- [x] T016 Update `compose.yml` to expose multiple FastAPI replicas behind a load balancer (e.g., Traefik)
- [ ] T017 Add integration tests for tiled processing and load‑balanced deployment

## Phase 4 – Innovative

- [ ] T018 Create plug‑in framework skeleton `app/plugins/__init__.py` and loader `app/plugins/loader.py`
- [ ] T019 Add sandbox endpoint `app/api/v1/sandbox.py` to execute a selected plug‑in on supplied data
- [ ] T020 Write a dummy plug‑in `app/plugins/example_plugin.py` that returns a static prediction
- [ ] T021 Add tests for plug‑in discovery and sandbox execution

## Phase 5 – GEDI Integration (Provable + Innovative)

- [x] T025 [P] Create `gedi_observations` table migration in `migrations/versions/0005_gedi_observations.py`
- [~] T026 [P] Add SQLAlchemy ORM model `app/models/gedi_observation.py` (footprint_id, acquisition_date, canopy_height, biomass, quality_flag, geom) <!-- PARTIAL: gedi_client.py is a stub (NotImplementedError) -->
- [~] T027 Implement GEDI client `app/services/gedi_client.py` — Earthdata auth, Level‑2A HDF5 fetch, and parse to records <!-- PARTIAL: gedi_client.py is a stub -->
- [ ] T028 Implement GEDI ingestion script `app/scripts/ingest_gedi.py` — reads HDF5 files, upserts into `gedi_observations`
- [ ] T029 Add Pydantic schemas `app/schemas/gedi.py` (GEDIRecord, GEDIIngestRequest, GEDIIngestResponse)
- [ ] T030 Add API endpoint `app/api/v1/gedi.py` — `POST /api/v1/gedi/ingest` and `GET /api/v1/gedi/observations`
- [ ] T031 Extend `/api/v1/metrics` to include GEDI‑derived KPIs (avg canopy height change, biomass delta per ROI)
- [ ] T032 [P] Write unit tests for GEDI client parsing and schema validation in `tests/unit/test_gedi_client.py`
- [x] T033 Write integration test `tests/integration/test_gedi_ingestion.py` covering upsert and metrics rollup
- [ ] T034 Update `AGENTS.md` Section 5 with GEDI API contract (Earthdata endpoint, auth, failure modes)
- [ ] T035 Update `docs/research/02-ARCHITECTURE.md` with GEDI data flow diagram notes

## Phase 6 – Documentation & Checklist

- [ ] T022 Update `docs/research/02-ARCHITECTURE.md` with SGI Way extensions (already added)
- [ ] T023 Create SGI checklist `specs/010-sgi-enhancements/checklists/requirements.md` using the unit‑test‑for‑requirements style
- [~] T024 Review and approve all new API specs in `specs/010-sgi-enhancements/spec.md` <!-- PARTIAL: spec.md exists but API specs not fully reviewed -->

---

## Audit Summary

**Audit Date:** 2026-04-30

**Statistics:**
- ✅ **COMPLETE:** 12 tasks (T001, T002, T003, T005, T006, T009, T010, T012, T014, T016, T025, T033)
- ⚠️ **PARTIAL:** 8 tasks (T004, T007, T011, T013, T015, T024, T026, T027)
- ❌ **NOT STARTED:** 15 tasks (T008, T017, T018, T019, T020, T021, T022, T023, T028, T029, T030, T031, T032, T034, T035)

**Partial Task Details:**
- T004: metrics endpoint exists but returns mock data
- T007: metrics_service exists but calculate_kpi_for_roi returns mock data
- T011: deterministic_runner exists but not verified in ML pipelines
- T013: dashboard has some shortcuts but not SGI-specific
- T015: tiling.py exists but scene ingestion integration not verified
- T024: spec.md exists but API specs not fully reviewed
- T026: gedi_client.py is a stub (NotImplementedError)
- T027: gedi_client.py is a stub

---
*Generated on 2026‑04‑23. Last audit: 2026‑04‑30.*
