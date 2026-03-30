# Tasks: Pillar II - Remote Sensing

**Input**: Design documents from `/specs/005-pillar2-remote-sensing/`
**Prerequisites**: `plan.md` (required), `research.md`, `data-model.md`, `contracts/scenes-api.md`, `quickstart.md`

**Tests**: Tests are required for this feature because the design artifacts explicitly define unit validation for index/cloud-mask logic and integration validation for the scene ingestion API and pipeline.

**Organization**: Tasks are grouped by user story so ingestion, retrieval, and resilience behavior can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **API**: `app/api/v1/`
- **Services**: `app/services/`
- **Schemas**: `app/schemas/`
- **Migrations**: `migrations/versions/`
- **Tests**: `tests/unit/`, `tests/integration/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish feature scaffolding and execution context before schema and service implementation.

- [x] T001 Confirm implementation work is on feature branch `005-pillar2-remote-sensing` before coding
- [x] T002 Create Pillar II scaffolding files: `app/services/stac_client.py`, `app/services/cloud_mask.py`, `app/services/indices.py`, `app/services/scene_ingestion.py`, `app/schemas/spectral.py`, `app/api/v1/scenes.py`, `tests/unit/test_indices.py`, `tests/unit/test_cloud_mask.py`, `tests/integration/test_scene_ingestion.py`, and `migrations/versions/0003_spectral_upsert_constraint.py`
- [x] T003 [P] Verify required dependencies are present for Pillar II in `pyproject.toml` (`pystac-client`, `planetary-computer`, `rasterio`, `numpy`) and add only missing entries
- [x] T004 [P] Register placeholder imports/router wiring targets in `app/api/v1/__init__.py` and `app/schemas/__init__.py` (if schema exports are used)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared data contracts and persistence primitives required by all user stories.

**CRITICAL**: No user story work should begin until this phase is complete.

- [x] T005 Implement migration `0003_spectral_upsert_constraint` in `migrations/versions/0003_spectral_upsert_constraint.py` adding UNIQUE(`roi_id`, `stac_item`) on `spectral_time_series`
- [x] T006 [P] Implement Pydantic models `SceneIngestRequest`, `SceneIngestResponse`, and `SpectralRecord` in `app/schemas/spectral.py` with date-range and platform validation
- [x] T007 [P] Implement Planetary Computer STAC query and item signing with 429 retry policy in `app/services/stac_client.py`
- [x] T008 [P] Implement QA60 cloud-fraction computation and mask threshold handling in `app/services/cloud_mask.py`
- [x] T009 [P] Implement windowed band reads and NDVI/ENDVI/Red-Edge computations in `app/services/indices.py`
- [x] T010 Implement batch orchestration and PostgreSQL upsert path in `app/services/scene_ingestion.py` using constraint `uq_spectral_roi_item`
- [x] T011 Implement scenes router skeleton in `app/api/v1/scenes.py` and register `/api/v1/scenes` in `app/api/v1/__init__.py`

**Checkpoint**: Data contracts, service primitives, and upsert foundation are ready for story delivery.

---

## Phase 3: User Story 1 - Ingest Spectral Scenes for an ROI (Priority: P1) 🎯 MVP

**Goal**: Allow users to ingest Planetary Computer scenes into `spectral_time_series` for a selected ROI and date window.

**Independent Test**: Call `POST /api/v1/scenes/ingest` with a valid ROI and verify response counters plus persisted rows (including masked-scene behavior).

### Tests for User Story 1

- [x] T012 [P] [US1] Add index formula unit tests in `tests/unit/test_indices.py` (NDVI, ENDVI, Red-Edge, zero-denominator, nodata)
- [x] T013 [P] [US1] Add QA60 cloud-mask unit tests in `tests/unit/test_cloud_mask.py` (clear, clouded, threshold boundary, cirrus, missing QA60 fallback)
- [x] T014 [P] [US1] Add ingestion integration tests in `tests/integration/test_scene_ingestion.py` covering clean scene persistence and masked scene persistence
- [x] T015 [P] [US1] Add validation integration tests in `tests/integration/test_scene_ingestion.py` for 422 behavior (`end_date < start_date`, invalid `platform`, malformed `roi_id`)

### Implementation for User Story 1

- [x] T016 [US1] Implement finalized index math and output clamping in `app/services/indices.py` to match `research.md` formulas
- [x] T017 [US1] Implement finalized QA60 bit-mask logic in `app/services/cloud_mask.py` with `cloud_cover > 0.20` masking contract
- [x] T018 [US1] Implement STAC discovery/signing flow in `app/services/stac_client.py` for date-range + ROI bbox queries
- [x] T019 [US1] Implement ingestion orchestration in `app/services/scene_ingestion.py` including per-item processing and commit lifecycle
- [x] T020 [US1] Implement `POST /api/v1/scenes/ingest` in `app/api/v1/scenes.py` returning `SceneIngestResponse`

**Checkpoint**: User Story 1 is complete when ingestion runs end-to-end and persists expected spectral rows.

---

## Phase 4: User Story 2 - Query Spectral Time Series (Priority: P2)

**Goal**: Allow users to list persisted spectral records by ROI/date filters for downstream Stage 1 consumption.

**Independent Test**: Call `GET /api/v1/scenes` with and without filters and verify date ordering, mask filtering, and schema shape.

### Tests for User Story 2

- [x] T021 [P] [US2] Add query integration coverage in `tests/integration/test_scene_ingestion.py` for `roi_id`, `start_date`, `end_date`, and `include_masked` filtering

### Implementation for User Story 2

- [x] T022 [US2] Implement `GET /api/v1/scenes` in `app/api/v1/scenes.py` with query filters and ascending `scene_date` ordering
- [x] T023 [US2] Finalize spectral response serialization in `app/schemas/spectral.py` for masked and unmasked records

**Checkpoint**: User Story 2 is complete when spectral records are retrievable with correct filtering and ordering semantics.

---

## Phase 5: User Story 3 - Enforce Resilience and Idempotency (Priority: P3)

**Goal**: Ensure ingestion is robust to partial failures and repeat runs without duplicate record creation.

**Independent Test**: Re-run ingest for same ROI/date range and verify update counts, skipped-scene accounting, partial continuation, and terminal STAC failure behavior.

### Tests for User Story 3

- [x] T024 [P] [US3] Extend `tests/integration/test_scene_ingestion.py` for upsert idempotency, missing-asset skip behavior, and 404 on unknown ROI
- [x] T025 [P] [US3] Add integration assertions in `tests/integration/test_scene_ingestion.py` that partial/missing STAC item assets are skipped while valid scenes continue and return 200 with `scenes_skipped` > 0
- [x] T026 [P] [US3] Add integration test in `tests/integration/test_scene_ingestion.py` for terminal STAC unavailability (retry exhaustion with zero usable scenes) returning HTTP 500 and clear error detail

### Implementation for User Story 3

- [x] T027 [US3] Implement per-scene exception handling, skip accounting, and warning logs in `app/services/scene_ingestion.py` so malformed/missing-asset items never abort the batch
- [x] T028 [US3] Implement retry-exhaustion handling in `app/services/stac_client.py` and map complete ingestion unavailability to HTTP 500 behavior in `app/api/v1/scenes.py`

**Checkpoint**: User Story 3 is complete when ingestion remains stable under failure scenarios and repeated runs are idempotent.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate full feature quality gate and completion standards.

- [x] T029 [P] Execute focused test runs for Pillar II files using `just test tests/unit/test_indices.py tests/unit/test_cloud_mask.py tests/integration/test_scene_ingestion.py`
- [x] T030 Add practical STAC discovery latency smoke check (target <= 15s for one-year window) in `tests/integration/test_scene_ingestion.py` or `app/scripts/` benchmark helper and document invocation in `specs/005-pillar2-remote-sensing/quickstart.md`
- [x] T031 Add practical end-to-end ingestion latency smoke check (target <= 60s for <= 100 scenes) in `tests/integration/test_scene_ingestion.py` or `app/scripts/` benchmark helper and document invocation in `specs/005-pillar2-remote-sensing/quickstart.md`
- [x] T032 Add practical `GET /api/v1/scenes` latency smoke check (target <= 2s for <= 365 ROI rows) in `tests/integration/test_scene_ingestion.py` or `app/scripts/` benchmark helper and document invocation in `specs/005-pillar2-remote-sensing/quickstart.md`
- [ ] T033 Execute full verification gate with `just verify` and resolve any lint/test regressions in `app/services/`, `app/api/v1/`, `app/schemas/`, and `tests/`
- [ ] T034 Validate quickstart flow in `specs/005-pillar2-remote-sensing/quickstart.md` (migration, ingest, list, masked-scene check, idempotency rerun, performance smoke checks)
- [x] T035 Update roadmap state in `AGENTS.md` Section 9 to mark Pillar II remote-sensing implementation items complete after acceptance

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 ingestion outputs and schema availability
- **User Story 3 (Phase 5)**: Depends on User Story 1 and User Story 2 behavior to validate resilience/idempotency paths
- **Polish (Phase 6)**: Depends on all implemented user stories

### User Story Dependencies

- **US1 (P1)**: First deliverable - ingestion pipeline and POST endpoint
- **US2 (P2)**: Depends on US1 persisted data model and router foundation
- **US3 (P3)**: Depends on US1 pipeline and US2 retrieval for complete operational validation

### Within Each User Story

- Tests before implementation
- Service logic before endpoint finalization
- Endpoint behavior before checkpoint validation

### Parallel Opportunities

- Setup: `T003` and `T004` can run in parallel
- Foundational: `T006`, `T007`, `T008`, and `T009` can run in parallel after `T005`
- US1: `T012`, `T013`, `T014`, and `T015` can run in parallel
- US2: Query tests (`T021`) can be authored in parallel with response-schema completion (`T023`)
- US3: Failure-path tests (`T024`, `T025`, `T026`) can run in parallel with implementation updates in `T027` and `T028`

---

## Parallel Example: User Story 1

```bash
# Parallel test implementation tasks
Task: "T012 [US1] Add index formula unit tests in tests/unit/test_indices.py"
Task: "T013 [US1] Add QA60 cloud-mask unit tests in tests/unit/test_cloud_mask.py"
Task: "T014 [US1] Add ingestion integration tests in tests/integration/test_scene_ingestion.py"
Task: "T015 [US1] Add validation integration tests in tests/integration/test_scene_ingestion.py"

# Parallel service implementation tasks after foundational setup
Task: "T016 [US1] Implement finalized index math in app/services/indices.py"
Task: "T017 [US1] Implement finalized QA60 logic in app/services/cloud_mask.py"
Task: "T018 [US1] Implement STAC discovery/signing flow in app/services/stac_client.py"
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Phase 1 and Phase 2
2. Complete Phase 3 (US1)
3. Validate ingestion endpoint independently before taking on retrieval/resilience enhancements

### Incremental Delivery

1. Deliver ingestion pipeline and persistence (US1)
2. Add query/list retrieval (US2)
3. Harden failure handling and idempotency (US3)
4. Run final quality and quickstart gates (Phase 6)

---

## Completion Criteria

- `migrations/versions/0003_spectral_upsert_constraint.py` applies cleanly with `just db-migrate`
- Unit tests for indices and cloud masking pass in `tests/unit/test_indices.py` and `tests/unit/test_cloud_mask.py`
- Integration coverage passes in `tests/integration/test_scene_ingestion.py` for ingestion, query, masking, and idempotency behavior
- Integration coverage passes in `tests/integration/test_scene_ingestion.py` for partial continuation, request validation (422), and terminal STAC unavailability (500) behavior
- `POST /api/v1/scenes/ingest` and `GET /api/v1/scenes` conform to `specs/005-pillar2-remote-sensing/contracts/scenes-api.md`
- Practical latency checks are documented and pass against targets (<= 15s STAC discovery, <= 60s ingestion batch for <= 100 scenes, <= 2s scene listing for <= 365 rows)
- Full gate `just verify` passes with zero failures