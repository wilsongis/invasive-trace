# Tasks: Wave 3 - AI Execution Chain

**Input**: Design documents from `/specs/007-wave3-ai-chain/`
**Prerequisites**: `plan.md` (required), `spec.md` (required)

**Tests**: Tests are required for this feature because the specification defines mandatory independent test criteria and acceptance scenarios for each user story.

**Organization**: Tasks are grouped by user story to keep each increment independently testable and dependency-ordered.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`US1`, `US2`, `US3`)
- Include exact file paths in every task description

## Phase 0: Research Preflight

**Purpose**: Satisfy the constitution's research-first gate before implementation begins.

- [x] W3-T001 Execute `just research-sync` and `just research-test` from repository root (`justfile`) and record the outcome or manual-login blocker in `AGENTS.md`

---

## Phase 1: Setup (Shared Scaffolding)

**Purpose**: Create Wave 3 module and test scaffolding before foundational service implementation.

- [x] W3-T002 Create Wave 3 scaffolding files `app/ml/stage1_anomaly.py`, `app/ml/stage2_classifier.py`, `app/ml/stage3_unet.py`, `app/services/ml_runtime.py`, `app/services/pipeline.py`, `app/services/feature_extractor.py`, `app/services/usgs_3dep_client.py`, `app/services/prediction_query.py`, `app/api/v1/predictions.py`, `app/schemas/pipeline.py`, `app/schemas/prediction.py`, `app/scripts/train_anomaly.py`, and `app/scripts/train_classifier.py`
- [x] W3-T003 [P] Register Wave 3 routers/schemas in `app/api/v1/__init__.py`, `app/api/v1/rois.py`, and `app/schemas/__init__.py` for pipeline trigger and prediction retrieval wiring

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared runtime contracts and resilient enrichment required by all user stories.

**CRITICAL**: Complete this phase before user story implementation.

- [x] W3-T004 Implement model runtime/version contracts and clamp helpers in `app/services/ml_runtime.py`, and implement full stage interfaces in `app/ml/stage1_anomaly.py` (`fit(roi_id, season_start, season_end)`, `predict(roi_id)`, `load()`), `app/ml/stage2_classifier.py` (`fit(X, y)`, `predict(X)`, `load()`), and `app/ml/stage3_unet.py` (`load()`, `infer(patch_tensor)`) with eager artifact-existence checks that raise a deterministic error before any DB write when the model file is absent; use exact paths `models/AnomalyDetector/anomaly-v0.1.0/model.joblib`, `models/FocalClassifier/rf-v0.1.0/model.joblib`, and `models/UNetTexture/unet-v0.1.0/model.pt`
- [x] W3-T005 [P] Implement executable training artifact generation in `app/scripts/train_anomaly.py` and `app/scripts/train_classifier.py` so both scripts produce registered artifacts that are loadable by the runtime wrappers in `app/ml/stage1_anomaly.py` and `app/ml/stage2_classifier.py`
- [x] W3-T006 [P] Implement Stage 2 feature assembly and resilient USGS 3DEP lookup with bounded retry/fallback in `app/services/feature_extractor.py` and `app/services/usgs_3dep_client.py`

**Checkpoint**: Stage wrappers, artifact contracts, clamp rules, and feature-enrichment primitives are ready.

---

## Phase 3: User Story 1 - Run the Full Pipeline for an ROI (Priority: P1) 🎯 MVP

**Goal**: Trigger Stage 1 -> Stage 2 -> Stage 3 and persist canonical prediction rows for a selected ROI.

**Independent Test**: Seed an ROI with unmasked `spectral_time_series` rows, call `POST /api/v1/rois/{id}/pipeline/run`, and assert `invasion_predictions` rows are created with `model_version='rf-v0.1.0'`, `confidence` in [0.0, 1.0], and non-null POINT geometry.

### Tests for User Story 1

- [x] W3-T007 [P] [US1] Add stage runtime, artifact compatibility, clamp, and **fail-fast tests** (each stage wrapper MUST raise a deterministic exception before any DB write when the model file is absent — one test per stage) in `tests/unit/test_stage1_anomaly.py`, `tests/unit/test_stage2_classifier.py`, and `tests/unit/test_stage3_unet.py`
- [x] W3-T008 [P] [US1] Add pipeline orchestration, lineage metadata, detection-point, and summary unit tests in `tests/unit/test_pipeline_service.py` and end-to-end pipeline run integration coverage in `tests/integration/test_pipeline_run.py`

### Implementation for User Story 1

- [x] W3-T009 [US1] Implement strict-order orchestration and prediction persistence in `app/services/pipeline.py` (Stage 1 -> Stage 2 -> Stage 3; `model_version='rf-v0.1.0'`; `validated=NULL`; clamp before insert; structured lineage logs and per-run sidecar metadata)
- [x] W3-T010 [US1] Implement deterministic Wave 3 detection-point and Stage 3 patch extraction in `app/services/pipeline.py` and `app/ml/stage3_unet.py`: derive the POINT from `ST_Centroid(regions_of_interest.geom)` in SRID 4326; resolve the Planetary Computer STAC item from `spectral_time_series.stac_item` for the anomalous scene date via `app/services/stac_client.py`; extract Sentinel-2 bands B04, B08, B03, B05 resampled to a common 10m grid; stack into a 512x512 four-channel tensor centered on the detection point with deterministic zero-padding or cropping at scene boundaries; if the STAC asset is unavailable, log the failure, skip that candidate, and continue with remaining candidates
- [x] W3-T011 [US1] Implement pipeline trigger endpoint and response schemas in `app/api/v1/rois.py` and `app/schemas/pipeline.py` for `POST /api/v1/rois/{id}/pipeline/run` including ROI 404 handling and descriptive zero-result `message` responses

**Checkpoint**: Full pipeline executes and persists valid predictions for a qualifying ROI.

---

## Phase 4: User Story 2 - Query Prediction Results as GeoJSON (Priority: P2)

**Goal**: Retrieve prediction results as a GeoJSON FeatureCollection with required filters and ordering.

**Independent Test**: Call `GET /api/v1/predictions` with `roi_id`, `validated`, `species_label`, and `min_hotspot_score` filters and verify valid GeoJSON output ordered by `hotspot_score DESC`.

### Tests for User Story 2

- [x] W3-T012 [P] [US2] Add GeoJSON query/filter integration tests in `tests/integration/test_predictions_geojson.py` for `roi_id`, `validated`, `species_label`, `min_hotspot_score`, empty result sets, omitted `validated` including pending rows, and default ordering

### Implementation for User Story 2

- [x] W3-T013 [US2] Implement GeoJSON prediction retrieval service and API contract in `app/services/prediction_query.py`, `app/api/v1/predictions.py`, and `app/schemas/prediction.py` with `validated=true|false` semantics and omitted `validated` returning all rows including pending

**Checkpoint**: Prediction retrieval API returns contract-compliant GeoJSON with filtering and ordering.

---

## Phase 5: User Story 3 - Handle Insufficient or Absent Spectral Data (Priority: P3)

**Goal**: Guarantee deterministic behavior for missing ROI, empty unmasked inputs, and USGS 3DEP failure paths.

**Independent Test**: Trigger `POST /api/v1/rois/{id}/pipeline/run` for non-existent ROI and ROI with zero unmasked spectral rows; verify 404 and `200` with `predictions_created: 0` plus a descriptive `message`, and Stage 2 fallback behavior when elevation retrieval fails.

### Tests for User Story 3

- [x] W3-T014 [P] [US3] Add resilience/fallback tests in `tests/unit/test_usgs_3dep_client.py` and `tests/unit/test_feature_extractor.py`, plus no-data and missing-ROI integration assertions in `tests/integration/test_pipeline_run.py`

### Implementation for User Story 3

- [x] W3-T015 [US3] Finalize no-data short-circuit and fallback semantics in `app/services/pipeline.py`, `app/services/usgs_3dep_client.py`, and `app/services/feature_extractor.py` (retry max 3, fallback elevation `0.0`, descriptive zero-result `message` summary)

**Checkpoint**: Pipeline is resilient and contract-compliant under absent or insufficient inputs.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Execute final quality gate before merge.

- [x] W3-T016 Execute full verification gate with `just verify` from repository root (`justfile`) and resolve any regressions in `app/api/v1/`, `app/services/`, `app/ml/`, `app/schemas/`, `app/scripts/`, and `tests/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 0 (Research Preflight)**: No dependencies; must complete before implementation begins.
- **Phase 1 (Setup)**: Depends on Phase 0.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US2)**: Depends on Phase 3 persisted prediction outputs.
- **Phase 5 (US3)**: Depends on Phase 3 runtime behavior and Phase 2 enrichment primitives.
- **Phase 6 (Polish)**: Depends on completion of all user stories.

### User Story Dependencies

- **US1 (P1)**: MVP and first deliverable.
- **US2 (P2)**: Depends on US1 producing predictions.
- **US3 (P3)**: Depends on US1 pipeline path and foundational enrichment logic.

### Parallel Opportunities

- Setup: `W3-T003` can run in parallel after `W3-T002` scaffolding exists.
- Foundational: `W3-T005` and `W3-T006` can run in parallel once `W3-T004` runtime contracts are established.
- US1: `W3-T007` and `W3-T008` can run in parallel.
- US2: `W3-T012` can run in parallel with schema wiring inside `W3-T013` after query contract is fixed.
- US3: `W3-T014` can run in parallel with implementation hardening in `W3-T015`.

---

## Parallel Example: User Story 1

```bash
Task: "W3-T007 [US1] Add stage runtime, artifact compatibility, and clamp unit tests in tests/unit/test_stage1_anomaly.py, tests/unit/test_stage2_classifier.py, tests/unit/test_stage3_unet.py"
Task: "W3-T008 [US1] Add pipeline orchestration, lineage metadata, detection-point, and summary unit/integration tests in tests/unit/test_pipeline_service.py and tests/integration/test_pipeline_run.py"
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Research Preflight (Phase 0), Setup (Phase 1), and Foundational work (Phase 2).
2. Deliver and validate US1 end-to-end pipeline run behavior.
3. Use US1 outputs to enable retrieval and resilience increments.

### Incremental Delivery

1. Complete research preflight and record status.
2. Deliver pipeline execution + persistence (US1).
3. Deliver GeoJSON retrieval API (US2).
4. Harden absent-data and fallback behavior (US3).
5. Run final quality gate (`just verify`) before merge.

---

## Completion Criteria

- Stage wrappers and artifact contracts are implemented in `app/ml/stage1_anomaly.py`, `app/ml/stage2_classifier.py`, and `app/ml/stage3_unet.py` with versions `anomaly-v0.1.0`, `rf-v0.1.0`, and `unet-v0.1.0`, and the Stage 1 and Stage 2 training scripts produce compatible artifacts.
- Pipeline orchestration in `app/services/pipeline.py` persists `invasion_predictions` with clamped `confidence`/`hotspot_score` and `model_version='rf-v0.1.0'`.
- `POST /api/v1/rois/{id}/pipeline/run` is implemented in `app/api/v1/rois.py` with ROI `404`, deterministic zero-result `message` responses, and lineage metadata capture.
- `GET /api/v1/predictions` is implemented in `app/api/v1/predictions.py` returning GeoJSON FeatureCollection via `app/services/prediction_query.py` and `app/schemas/prediction.py` with fixed `validated` filter semantics.
- Required unit and integration tests are added in `tests/unit/` and `tests/integration/` for all three user stories.
- Full quality gate `just verify` passes from repository root.
