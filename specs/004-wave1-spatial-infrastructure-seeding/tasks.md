# Tasks: Wave 1 - Pillar I Spatial Infrastructure & Seeding

**Input**: Design documents from `/specs/004-wave1-spatial-infrastructure-seeding/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Tests are required because the spec explicitly requires ROI API validation, migration correctness, retry behavior, and seeded-record verification.

**Organization**: Tasks are grouped by user story so schema/ROI work, source seeding, and ROI-scoped sync can each be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Invasive Trace canonical layout**: `app/api/v1/`, `app/models/`, `app/services/`, `app/scripts/`, `app/schemas/`
- **Tests**: `tests/unit/`, `tests/integration/`
- **Migrations**: `migrations/` (Alembic)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the module layout and imports needed before schema and API work begins.

- [ ] T000 Confirm implementation is running on feature branch `004-wave1-spatial-infrastructure-seeding` (or another valid Spec Kit feature branch), not on `main`
- [ ] T001 Create Wave 1 file scaffolding in `app/models/roi.py`, `app/models/prediction.py`, `app/models/observation.py`, `app/models/spectral.py`, `app/api/v1/rois.py`, `app/api/v1/observations.py`, `app/schemas/roi.py`, `app/services/inat_consumer.py`, `app/services/eddmaps_consumer.py`, and `app/scripts/seed_observations.py`
- [ ] T002 [P] Wire package exports/imports in `app/models/__init__.py`, `app/api/v1/__init__.py`, and any new `app/schemas/__init__.py` needed for Wave 1 routing and Alembic discovery
- [ ] T003 [P] Verify `just seed-data`, `just db-revision`, and `just db-migrate` command paths remain aligned with Wave 1 implementation files in `justfile`
- [ ] T003A [P] Run `just research-sync` and `just research-test` as Wave 1 preflight and record command outcomes in Wave 1 implementation notes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the canonical schema and migration foundation required before user story work can proceed.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [ ] T004 Create `RegionOfInterest` ORM model in `app/models/roi.py` matching `AGENTS.md` Section 4 exactly (`GEOMETRY(POLYGON, 4326)`, GiST index)
- [ ] T005 [P] Create `InvasionPrediction` ORM model in `app/models/prediction.py` with `GEOMETRY(POINT, 4326)`, `confidence` CHECK 0.0–1.0, FK to `regions_of_interest`, and preserved tri-state validation semantics
- [ ] T006 [P] Create `GroundTruthObservation` ORM model in `app/models/observation.py` with source CHECK constraint, `raw_payload JSONB`, and canonical geometry
- [ ] T007 [P] Create `SpectralTimeSeries` ORM model in `app/models/spectral.py` with platform CHECK constraint and `is_masked BOOLEAN`
- [ ] T008 Autogenerate Alembic migration in `migrations/versions/` using `just db-revision msg="create four canonical tables"` and review the output for geometry columns, GiST indexes, FKs, and CHECK constraints
- [ ] T009 Apply the migration with `just db-migrate` and confirm all four canonical tables exist in PostGIS
- [ ] T009A Validate and document that `invasion_predictions.model_version` semantics remain Stage-2-lineage aligned (`rf-v0.1.0` style registry value), alongside tri-state `validated` semantics

**Checkpoint**: Canonical schema is live and ROI/API work can proceed.

---

## Phase 3: User Story 1 - Create and Query Regions of Interest (Priority: P1) 🎯 MVP

**Goal**: Make the canonical schema queryable through ROI create/list/fetch endpoints.

**Independent Test**: Apply the migration, create an ROI through `POST /api/v1/rois`, and verify list/fetch responses return persisted geometry as GeoJSON.

### Tests for User Story 1

- [ ] T010 [P] [US1] Add ROI schema round-trip tests in `tests/unit/test_roi_schemas.py` validating WKT polygon input to GeoJSON output behavior
- [ ] T011 [P] [US1] Add ROI endpoint integration coverage in `tests/integration/test_roi_endpoints.py` for create/list/fetch behavior and GeoJSON responses

### Implementation for User Story 1

- [ ] T012 [US1] Implement `ROICreate` and `ROIResponse` schemas in `app/schemas/roi.py` for WKT polygon input and GeoJSON geometry output
- [ ] T013 [US1] Implement `POST /api/v1/rois`, `GET /api/v1/rois/{id}`, and `GET /api/v1/rois` in `app/api/v1/rois.py`
- [ ] T014 [US1] Register the ROI router in `app/api/v1/__init__.py` and ensure invalid geometry inputs are rejected without partial writes

**Checkpoint**: User Story 1 is complete when ROIs can be created, listed, and fetched through the API.

---

## Phase 4: User Story 2 - Seed Ground-Truth Observations (Priority: P2)

**Goal**: Ingest iNaturalist and EDDMapS observations into `ground_truth_observations` with resilient source handling.

**Independent Test**: Run the seed workflow and confirm at least one observation row is stored with canonical fields and raw payload persistence.

### Tests for User Story 2

- [ ] T015 [P] [US2] Add retry-and-skip behavior tests in `tests/unit/test_inat_consumer.py` covering HTTP 429 recovery and max-retry log behavior
- [ ] T016 [P] [US2] Add equivalent retry-and-skip behavior tests in `tests/unit/test_eddmaps_consumer.py`
- [ ] T016A [P] [US2] Add deterministic duplicate-handling tests in `tests/unit/test_eddmaps_consumer.py` for repeated sync inputs

### Implementation for User Story 2

- [ ] T017 [US2] Implement the async iNaturalist consumer in `app/services/inat_consumer.py` with exponential backoff, log-and-skip behavior, and writes to `ground_truth_observations`
- [ ] T018 [US2] Implement the async EDDMapS consumer in `app/services/eddmaps_consumer.py` with the same resilience contract and persistence behavior
- [ ] T019 [US2] Implement the CLI seed entry point in `app/scripts/seed_observations.py` for configurable taxon list and bounding box input, wired to `just seed-data`
- [ ] T019A [US2] Implement deterministic duplicate handling in `app/services/inat_consumer.py` and `app/services/eddmaps_consumer.py` (idempotent upsert or skip-on-conflict strategy)

**Checkpoint**: User Story 2 is complete when source-backed seeding inserts observation records without crashing on partial source failure.

---

## Phase 5: User Story 3 - Run ROI-Scoped Observation Sync (Priority: P3)

**Goal**: Expose observation seeding through an ROI-scoped API endpoint with a structured summary payload.

**Independent Test**: Create an ROI, call `POST /api/v1/observations/sync`, and verify the response reports sources polled, inserted records, and skipped records.

### Tests for User Story 3

- [ ] T020 [P] [US3] Add ROI-scoped sync integration coverage in `tests/integration/test_observation_sync.py` for success, partial failure, and missing-ROI error handling

### Implementation for User Story 3

- [ ] T021 [US3] Implement `POST /api/v1/observations/sync` in `app/api/v1/observations.py` to resolve the ROI, invoke both consumers, and return `sources_polled`, `records_inserted`, and `records_skipped`
- [ ] T022 [US3] Register the observation sync router in `app/api/v1/__init__.py` and ensure missing ROI requests return a clear application error

**Checkpoint**: User Story 3 is complete when ROI-scoped sync works through the API and preserves partial-success reporting.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final Wave 1 validation before remote-sensing work begins.

- [x] T023 [P] Confirm Wave 1 remains scoped to spatial infrastructure and seeding only; no STAC, index-calculation, or scene-ingestion code is introduced
- [x] T024 [P] Run `just db-migrate`, `just seed-data`, and `just verify`, then resolve any Wave 1 regressions
- [x] T025 Validate Wave 1 checkpoint criteria: canonical tables created, at least one observation inserted, and `POST /api/v1/rois` returns HTTP 201 with GeoJSON geometry
- [x] T026 Update `AGENTS.md` and `TODO.md` after Wave 1 artifact generation or completion state changes are validated
- [x] T027 Capture SC-004 evidence by recording all observed HTTP 429 events and whether each recovered within retry budget or was logged-and-skipped during validation runs
- [x] T028 [P] Add canonical schema contract integration assertions in `tests/integration/test_db_connection.py` covering four canonical table existence, SRID 4326 geometry enforcement, GiST indexes, required foreign keys, and CHECK constraints
- [x] T029 Define deterministic duplicate identity in `app/models/observation.py` by adding a unique key strategy for source plus external_id records and documenting NULL external_id behavior
- [x] T030 Apply the duplicate identity guard in the Wave 1 migration file under `migrations/versions/` by creating a unique index for `ground_truth_observations` on source and external_id with NULL-safe behavior
- [x] T031 [P] Add explicit retry policy constants in `app/services/inat_consumer.py` and `app/services/eddmaps_consumer.py`, including base delay, exponential factor, max retries, jitter policy, and max retry budget
- [x] T032 [P] Implement request timeout and cancellation handling in `app/services/inat_consumer.py`, `app/services/eddmaps_consumer.py`, and `app/api/v1/observations.py` so timed-out sources return partial-success summaries without process crashes
- [x] T033 [P] Add sync-run audit logging in `app/api/v1/observations.py` and `app/scripts/seed_observations.py` with sync_run_id, roi_id, source, retry_count, records_inserted, records_skipped, and failure_class fields
- [x] T034 [P] Harden ROI geometry validation in `app/schemas/roi.py` and `app/api/v1/rois.py` by enforcing valid polygon geometry, rejecting self-intersections, and normalizing to SRID 4326 before persistence
- [x] T035 [P] Make retry tests deterministic in `tests/unit/test_inat_consumer.py` and `tests/unit/test_eddmaps_consumer.py` by mocking sleep/time behavior, seeding jitter values, and asserting exact retry schedules
- [x] T036 Add dry-run support for seeding in `app/scripts/seed_observations.py` and wire command exposure in `justfile` so planned inserts/skips are reported without database writes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on canonical schema completion
- **User Story 2 (Phase 4)**: Depends on canonical schema completion and benefits from ROI foundation work
- **User Story 3 (Phase 5)**: Depends on both ROI endpoints and source consumers
- **Polish (Phase 6)**: Depends on all targeted user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: First deliverable — establishes queryable spatial foundation
- **User Story 2 (P2)**: Depends on the schema but is otherwise independently valuable
- **User Story 3 (P3)**: Depends on User Stories 1 and 2

### Within Each User Story

- Tests before implementation where test artifacts are specified
- Models before migration
- Migration before ROI/API and seeding validation
- Consumers before CLI and sync endpoint integration
- Checkpoint validation before roadmap status updates
- T030 depends on T029
- T032 depends on T031
- T035 depends on T031
- T036 depends on T019

### Parallel Opportunities

- `T002` and `T003` can run in parallel during Setup
- `T005`, `T006`, and `T007` can run in parallel after `T004`
- `T010` and `T011` can run in parallel for US1
- `T015` and `T016` can run in parallel for US2
- `T028`, `T031`, `T033`, and `T034` can run in parallel during Phase 6

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases
2. Complete User Story 1 and validate the ROI API independently
3. Stop and verify the schema plus ROI foundation before beginning source seeding

### Incremental Delivery

1. Deliver canonical schema + ROI API
2. Add resilient source seeding
3. Add ROI-scoped sync endpoint
4. Validate the Wave 1 checkpoint before moving to Wave 2
