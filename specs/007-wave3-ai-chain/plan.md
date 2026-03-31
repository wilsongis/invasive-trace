# Implementation Plan: Wave 3 - AI Execution Chain

**Branch**: `007-wave3-ai-chain` | **Date**: 2026-03-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-wave3-ai-chain/spec.md`

**Note**: This plan delivers Wave 3 Phases 3A-3D only. It assumes Wave 1 canonical schema and Wave 2 spectral ingestion are already in place, and it introduces no schema migrations.

## Summary

Wave 3 implements the end-to-end AI execution chain that transforms `spectral_time_series` into `invasion_predictions` through three ordered stages:

1. Stage 1 `AnomalyDetector` (`anomaly-v0.1.0`) identifies anomalous NDVI scenes for an ROI.
2. Stage 2 `FocalClassifier` (`rf-v0.1.0`) classifies species and confidence from `[ndvi, endvi, red_edge, elevation]`.
3. Stage 3 `UNetTexture` (`unet-v0.1.0`) computes hotspot risk from spatial texture.

The orchestrator persists prediction rows with `model_version=rf-v0.1.0` only, while Stage 1/Stage 3 versions are logged as lineage metadata. API delivery includes pipeline execution (`POST /api/v1/rois/{id}/pipeline/run`) and GeoJSON retrieval (`GET /api/v1/predictions`) with filtering.

## Technical Context

<!-- Stack is LOCKED — do not change these values without a constitution amendment. -->

**Language/Version**: Python 3.12 (managed by `uv`)
**Primary Dependencies**: FastAPI, SQLAlchemy (async) + GeoAlchemy2, scikit-learn, PyTorch, joblib, httpx, Pydantic, numpy
**Storage**: PostgreSQL 16 + PostGIS 3.4 — existing canonical tables only (`regions_of_interest`, `invasion_predictions`, `ground_truth_observations`, `spectral_time_series`)
**Testing**: `pytest` + `pytest-asyncio` via `just test`
**Target Platform**: Podman-containerized Linux (macOS dev via `just run`)
**Project Type**: Geospatial AI web service
**Performance Goals**:
- `POST /api/v1/rois/{id}/pipeline/run` completes within 120 seconds for ROIs with <= 50 unmasked spectral rows.
- `GET /api/v1/predictions` responds within 2 seconds for <= 2,000 predictions per ROI in local validation.
**Constraints**:
- No schema/table/column changes in Wave 3; no Alembic migration.
- `invasion_predictions.model_version` stores Stage 2 version `rf-v0.1.0` only.
- `confidence` and `hotspot_score` values are clamped to [0.0, 1.0] before persistence.
- External API consumers follow retry/fallback policy (HTTP 429 => exponential backoff max 3 retries).
- All execution paths use FastAPI + async SQLAlchemy + `uv`/`just` workflow.
**Scale/Scope**: Single-ROI pipeline runs for functional validation; batch automation is out of scope for this wave.

## Constitution Check

*GATE: Must pass before implementation begins. Re-check after detailed design completion.*

Verify ALL of the following before proceeding:

- [x] **Anti-Context Rot (II)**: Checked `AGENTS.md` Sections 4, 5, 6; schema contracts, API URL contracts, and model versions are sourced verbatim.
- [x] **Tech Stack (III)**: Plan uses mandated stack only (FastAPI, async SQLAlchemy, PostGIS, scikit-learn, PyTorch, Ruff, pytest, `uv`, `just`).
- [x] **Spatial Integrity (IV)**: No schema changes are planned; Wave 3 writes only to existing `invasion_predictions` columns with SRID 4326 geometry.
- [x] **API Resilience (V)**: USGS 3DEP integration enforces bounded exponential backoff (3 retries) and fallback `elevation=0.0` with warning logs.
- [x] **ML Registry (VI)**: Model versions are fixed to `anomaly-v0.1.0`, `rf-v0.1.0`, `unet-v0.1.0`; DB lineage rule for `model_version` is preserved.
- [ ] **Research-First (I)**: Execute `just research-sync` and `just research-test` before coding begins; log result in implementation notes.

*Conclusion: GATE READY FOR IMPLEMENTATION PLANNING. No constitution violations identified.*

## Project Structure

### Documentation (this feature)

```text
specs/007-wave3-ai-chain/
├── spec.md              # Feature specification
├── plan.md              # This file
└── tasks.md             # Follow-on executable task list
```

### Source Code (repository root)

```text
app/
├── api/v1/
│   ├── rois.py                     # UPDATE: add POST /api/v1/rois/{id}/pipeline/run
│   ├── predictions.py              # NEW: GET /api/v1/predictions (GeoJSON)
│   └── __init__.py                 # UPDATE: register predictions router
├── schemas/
│   ├── pipeline.py                 # NEW: pipeline run request/response schemas
│   └── prediction.py               # NEW: GeoJSON feature/property response schemas
├── services/
│   ├── pipeline.py                 # NEW: run_pipeline(roi_id) orchestrator
│   ├── feature_extractor.py        # NEW: Stage 2 feature assembly from spectral + elevation
│   ├── usgs_3dep_client.py         # NEW: resilient elevation lookup with retry/fallback
│   ├── prediction_query.py         # NEW: filtered prediction retrieval + GeoJSON transform
│   └── ml_runtime.py               # NEW: shared artifact loading + clamp helpers
├── ml/
│   ├── stage1_anomaly.py           # NEW: AnomalyDetector wrapper, fit/load/predict
│   ├── stage2_classifier.py        # NEW: FocalClassifier wrapper, fit/load/predict
│   └── stage3_unet.py              # NEW: UNetTexture wrapper, load/infer
└── scripts/
    ├── train_anomaly.py            # NEW: Stage 1 training artifact script
    └── train_classifier.py         # NEW: Stage 2 training artifact script

tests/
├── unit/
│   ├── test_stage1_anomaly.py      # NEW: Stage 1 filtering + anomaly outputs
│   ├── test_stage2_classifier.py   # NEW: Stage 2 output shape + confidence clamp
│   ├── test_stage3_unet.py         # NEW: Stage 3 score clamp + artifact loading
│   ├── test_usgs_3dep_client.py    # NEW: retry budget + fallback behavior
│   ├── test_feature_extractor.py   # NEW: vector shape and null-handling behavior
│   └── test_pipeline_service.py    # NEW: orchestration order and summary payload
└── integration/
    ├── test_pipeline_run.py        # NEW: POST /pipeline/run end-to-end DB write path
    └── test_predictions_geojson.py # NEW: GET /predictions filters + ordering + schema
```

**Structure Decision**: Wave 3 introduces explicit ML stage wrappers under `app/ml/`, orchestration and external client logic under `app/services/`, and thin API routers under `app/api/v1/`. Existing ORM models remain unchanged and no migrations are created.

## Implementation Phases (Wave 3)

### Phase 3A - Model Runtime and Artifact Contracts

**Goal**: Implement typed runtime wrappers for all three stages with strict artifact loading and version enforcement.

**Files**:
- `app/ml/stage1_anomaly.py`
- `app/ml/stage2_classifier.py`
- `app/ml/stage3_unet.py`
- `app/services/ml_runtime.py`
- `app/scripts/train_anomaly.py`
- `app/scripts/train_classifier.py`

**Tasks**:
- Define constants for model versions and artifact paths exactly:
  - `models/AnomalyDetector/anomaly-v0.1.0/model.joblib`
  - `models/FocalClassifier/rf-v0.1.0/model.joblib`
  - `models/UNetTexture/unet-v0.1.0/model.pt`
- Implement eager artifact existence checks with clear exceptions before inference starts.
- Implement confidence/hotspot clamp utility in `ml_runtime.py` to enforce [0.0, 1.0].
- Stage 1 input contract: unmasked NDVI only (`is_masked=FALSE`) ordered by `scene_date`.
- Stage 2 output contract: `(species_label, confidence)` with non-empty species and clamped confidence.
- Stage 3 output contract: `hotspot_score` clamped to [0.0, 1.0].

**Exit Criteria**:
- Missing artifact raises deterministic startup/runtime error before DB writes.
- All stage wrappers expose deterministic interfaces used by orchestrator.

### Phase 3B - Feature Extraction and External Enrichment

**Goal**: Build Stage 2-ready feature vectors using spectral values plus resilient USGS 3DEP elevation lookup.

**Files**:
- `app/services/feature_extractor.py`
- `app/services/usgs_3dep_client.py`

**Tasks**:
- Implement `fetch_elevation(lat, lon)` in `usgs_3dep_client.py` using `https://tnmapi.cr.usgs.gov/api/`.
- Apply bounded exponential backoff for HTTP 429 with `MAX_RETRIES=3`.
- On retry exhaustion or non-recoverable API failure, return fallback elevation `0.0` and emit warning log.
- Build `[ndvi, endvi, red_edge, elevation]` vectors in `feature_extractor.py` with null-safe handling:
  - Skip rows that cannot produce complete spectral values.
  - Continue processing remaining candidates.
- Add guardrails for empty candidate sets to return deterministic empty pipeline results (`predictions_created: 0`).

**Exit Criteria**:
- Elevation failures never crash the request lifecycle.
- Feature extractor produces valid vectors or an empty result with descriptive summary.

### Phase 3C - Pipeline Orchestration and Prediction Persistence

**Goal**: Implement `run_pipeline(roi_id)` that executes Stage 1 -> Stage 2 -> Stage 3 and writes canonical predictions.

**Files**:
- `app/services/pipeline.py`
- `app/api/v1/rois.py` (pipeline trigger route addition)
- `app/schemas/pipeline.py`

**Tasks**:
- Validate ROI existence; return `404` via API layer if missing.
- Query unmasked spectral rows for ROI; short-circuit with `predictions_created: 0` when empty.
- Execute stage chain in strict order and record structured lineage logs for Stage 1 and Stage 3 versions.
- Persist `invasion_predictions` rows with:
  - `model_version='rf-v0.1.0'` only
  - `validated=NULL`, `validator_notes=NULL`
  - `geom` as POINT SRID 4326
- Guarantee `confidence` and `hotspot_score` are clamped before insert.
- Return summary payload `{roi_id, predictions_created, model_version}`.

**Exit Criteria**:
- Pipeline run endpoint creates records for valid ROI input and returns zero-result success when inputs are insufficient.
- No migration or schema alteration introduced.

### Phase 3D - Prediction Retrieval API and Hardening

**Goal**: Expose prediction results as GeoJSON FeatureCollection with contract-compliant filters and ordering.

**Files**:
- `app/api/v1/predictions.py`
- `app/services/prediction_query.py`
- `app/schemas/prediction.py`
- `app/api/v1/__init__.py` (router registration)

**Tasks**:
- Implement `GET /api/v1/predictions` with optional filters:
  - `roi_id`
  - `species_label`
  - `validated`
  - `min_hotspot_score`
- Map DB rows to GeoJSON FeatureCollection with required properties.
- Default ordering `hotspot_score DESC` (aligned to `idx_pred_score`).
- Ensure empty match set returns `200` with empty `features`.

**Exit Criteria**:
- GeoJSON schema and filters satisfy all FR/SC contracts in spec.
- Response remains stable across mixed `validated` states and score distributions.

## Test Strategy

### Unit Tests

- Stage wrappers: artifact loading, output typing, clamp behavior.
- `usgs_3dep_client`: 429 retry schedule, retry exhaustion fallback `0.0`, warning log emission.
- `feature_extractor`: vector build from spectral rows, skip invalid rows, empty-result handling.
- `pipeline` service: call-order validation (3A -> 3B -> 3C), no-write behavior on empty inputs.
- `prediction_query`: filter combinations and deterministic ordering.

### Integration Tests

- `POST /api/v1/rois/{id}/pipeline/run`:
  - ROI missing -> `404`
  - ROI with no unmasked spectral rows -> `200` + `predictions_created: 0`
  - ROI with qualifying data -> inserts predictions with `model_version='rf-v0.1.0'`
- `GET /api/v1/predictions`:
  - Valid GeoJSON structure
  - Filter behavior (`roi_id`, `validated`, `min_hotspot_score`, `species_label`)
  - Default descending `hotspot_score` ordering

### Quality Gates

- `just lint` must pass with zero Ruff violations.
- `just test` must pass all unit and integration suites.
- `just verify` must pass as final merge gate.

## Risk Register

| Risk | Impact | Mitigation | Owner |
| :--- | :--- | :--- | :--- |
| Missing model artifacts at runtime (`model.joblib` / `model.pt`) | Pipeline starts but fails after partial work, risking inconsistent outputs | Enforce startup/eager artifact checks in Phase 3A and fail fast before DB writes with explicit error message and path | Wave 3 implementer |
| Empty or fully masked spectral inputs (`is_masked=TRUE` or null vectors) | No usable features cause runtime exceptions or misleading success claims | Add deterministic short-circuit in pipeline (`predictions_created: 0`) and explicit summary messaging; unit + integration coverage for empty input paths | Wave 3 implementer |
| USGS 3DEP instability/rate limiting (HTTP 429, timeout, partial response) | Stage 2 feature extraction blocks prediction generation | Implement bounded exponential retry (max 3), warning logs, and fallback `elevation=0.0`; validate with dedicated unit tests and integration mocks | Wave 3 implementer |

## Execution Checklist

1. Implement Phase 3A files and tests.
2. Implement Phase 3B files and tests.
3. Implement Phase 3C endpoint + persistence behavior and integration tests.
4. Implement Phase 3D GeoJSON endpoint and integration tests.
5. Run `just lint`, `just test`, and `just verify` before opening PR.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :-------- | :--------- | :---------------------------------- |
| None | N/A | N/A |
