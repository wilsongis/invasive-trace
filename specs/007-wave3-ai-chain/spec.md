# Feature Specification: [FEATURE NAME]

# Feature Specification: Wave 3 — AI Execution Chain

**Feature Branch**: `007-wave3-ai-chain`
**Created**: 2026-03-31
**Status**: Ready for Implementation
**Input**: User description: "Wave 3: AI Execution Chain — three-stage ML pipeline (AnomalyDetector, FocalClassifier, UNetTexture) producing invasion_predictions with hotspot scores"

## Overview

Wave 3 delivers the three-stage AI execution chain that transforms persisted spectral time-series data into actionable invasion prediction records for the Southern Grassland Institute. It depends directly on Wave 2 (`spectral_time_series` populated by Sentinel-2 scene ingestion) and produces `invasion_predictions` rows that will be reviewed by field experts in Wave 4.

The chain runs in strict sequence:

1. **Stage 1 — AnomalyDetector (`anomaly-v0.1.0`)**: Detects seasonal green-up departures in an ROI's NDVI time series and returns a shortlist of anomalous scene dates with departure scores.
2. **Stage 2 — FocalClassifier (`rf-v0.1.0`)**: Classifies anomalous pixels using a spectral feature vector (`ndvi`, `endvi`, `red_edge`, `elevation`) to produce a species label and confidence score.
3. **Stage 3 — UNetTexture (`unet-v0.1.0`)**: Scores spatial texture of 512×512 image patches to produce a hotspot risk float in [0, 1].

A pipeline orchestrator (`run_pipeline`) chains all three stages for a given ROI and writes one `InvasionPrediction` record per anomalous scene candidate. In Wave 3, the detection point for each candidate is the ROI centroid in WGS84, and the Stage 3 patch is extracted as a 512x512 raster window centered on that point for the anomalous scene date.

## Goals

- Deliver a deterministic, end-to-end AI execution path from spectral time-series data to spatial prediction records.
- Enforce model registry version semantics from `AGENTS.md` Section 6 so all artifacts are traceable.
- Persist prediction lineage correctly: `model_version` column stores the Stage 2 classifier version (`rf-v0.1.0`); Stage 1 and Stage 3 versions are captured in structured logs and a per-run sidecar metadata payload.
- Expose an API endpoint to trigger the full pipeline for a specified ROI and a separate endpoint to query predictions as a GeoJSON FeatureCollection.
- Guarantee all `confidence` values satisfy the DB check constraint (0.0–1.0) and all `hotspot_score` values are in [0, 1].

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Run the Full Pipeline for an ROI (Priority: P1)

As a project contributor who has ingested spectral scenes for an ROI, I need to trigger the three-stage AI pipeline so the system produces invasion prediction records for that region.

**Why this priority**: The pipeline is the primary deliverable of Wave 3; no predictions exist until it runs.

**Independent Test**: Can be fully tested by seeding one ROI with spectral rows, calling `POST /api/v1/rois/{id}/pipeline/run`, and asserting that at least one `InvasionPrediction` row exists in the database with a valid `model_version`, `confidence` in [0.0, 1.0], and a non-null `geom`.

**Acceptance Scenarios**:

1. **Given** an ROI with at least one unmasked `spectral_time_series` row, **When** `POST /api/v1/rois/{id}/pipeline/run` is called, **Then** the system runs all three stages in order and returns a `200` response with a count of predictions created.
2. **Given** Stage 1 identifies at least one anomalous scene, **When** Stage 2 classifies the corresponding feature vector, **Then** the returned `species_label` is a non-empty string and `confidence` is in [0.0, 1.0].
3. **Given** Stage 2 returns a prediction, **When** Stage 3 evaluates the spatial patch, **Then** `hotspot_score` is a float in [0.0, 1.0] and is persisted to `invasion_predictions.hotspot_score`.
4. **Given** a prediction is written, **When** the `invasion_predictions` row is inspected, **Then** `model_version` equals `rf-v0.1.0`, `validated` is `NULL`, and `predicted_at` is set.

---

### User Story 2 — Query Prediction Results as GeoJSON (Priority: P2)

As a data analyst preparing data for field review, I need to retrieve all invasion predictions for an ROI as a GeoJSON FeatureCollection so I can visualise and filter results before handing off to Wave 4.

**Why this priority**: Retrieval is needed immediately after pipeline execution to validate output quality but depends on predictions existing first.

**Independent Test**: Can be fully tested by calling `GET /api/v1/predictions` with `roi_id` and optional filter params and verifying that the response is a valid GeoJSON FeatureCollection with correctly structured feature properties.

**Acceptance Scenarios**:

1. **Given** predictions exist for an ROI, **When** `GET /api/v1/predictions?roi_id={id}` is called, **Then** a GeoJSON FeatureCollection is returned containing one Feature per prediction with `species_label`, `confidence`, `hotspot_score`, `model_version`, and `validated` as properties.
2. **Given** predictions exist with mixed `validated` states, **When** `GET /api/v1/predictions?validated=false` is used, **Then** only rejected predictions are returned.
3. **Given** predictions exist with varying `hotspot_score` values, **When** `GET /api/v1/predictions?min_hotspot_score=0.7` is used, **Then** only predictions with `hotspot_score >= 0.7` are returned.
4. **Given** no predictions match the filter, **When** the endpoint is queried, **Then** the API returns `200` with an empty `features` array.

---

### User Story 3 — Handle Insufficient or Absent Spectral Data (Priority: P3)

As a maintainer, I need the pipeline to respond predictably when an ROI has no usable spectral data so that partial or missing input does not cause unhandled failures.

**Why this priority**: Operational reliability requires clear failure semantics before the pipeline is exposed to batch use.

**Independent Test**: Can be fully tested by calling `POST /api/v1/rois/{id}/pipeline/run` for an ROI with zero unmasked spectral rows and for a non-existent ROI, verifying the appropriate error responses.

**Acceptance Scenarios**:

1. **Given** an ROI that does not exist, **When** the pipeline is triggered, **Then** the API returns `404` and no pipeline stages execute.
2. **Given** an ROI that exists but has zero unmasked `spectral_time_series` rows, **When** the pipeline is triggered, **Then** the API returns `200` with `predictions_created: 0` and a descriptive `message` field — it MUST NOT raise an unhandled exception.
3. **Given** USGS 3DEP elevation lookup fails for a prediction point, **When** Stage 2 feature construction runs, **Then** the pipeline logs the failure, uses a fallback elevation of `0.0`, and continues processing the remaining points.

---

### Edge Cases

- ROI exists but Stage 1 finds zero anomalous scenes in the NDVI time series (pipeline returns `predictions_created: 0`).
- `spectral_time_series` rows for the ROI are all masked (`is_masked=TRUE`); Stage 1 has no valid NDVI values to analyse.
- Stage 2 classifier returns `confidence` outside [0.0, 1.0] due to numerical instability; the value MUST be clamped before a DB write to satisfy the `CHECK` constraint.
- Stage 3 U-Net returns a value outside [0.0, 1.0]; the value MUST be clamped to [0.0, 1.0] before persistence.
- USGS 3DEP API returns HTTP 429; the elevation consumer MUST apply exponential backoff (max 3 retries) then fall back to `elevation=0.0` for that point.
- USGS 3DEP returns elevation data that is spatially misaligned with the prediction point; Stage 2 proceeds with the nearest available value.
- Pipeline is triggered a second time for the same ROI; duplicate predictions for the same point geometry and `predicted_at` are possible and are treated as separate inference runs (no upsert constraint on `invasion_predictions`).
- Model artifact file is missing from `models/` at pipeline startup; the system MUST raise a clear error at load time before any DB writes occur.

## Requirements *(mandatory)*

### Functional Requirements

**Stage 1 — AnomalyDetector**

- **FR-001**: The system MUST implement an `AnomalyDetector` class that trains on historical NDVI values from `spectral_time_series` for a given ROI and date window, using IsolationForest methodology.
- **FR-002**: `AnomalyDetector.predict(roi_id)` MUST return a list of `(scene_date, departure_score)` tuples representing scenes where NDVI departs significantly from the historical baseline.
- **FR-003**: The `AnomalyDetector` model version string MUST be `anomaly-v0.1.0` as registered in `AGENTS.md` Section 6.
- **FR-004**: The trained model artifact MUST be saved to and loaded from `models/AnomalyDetector/anomaly-v0.1.0/model.joblib`.
- **FR-005**: Stage 1 MUST source NDVI values exclusively from `spectral_time_series` rows where `is_masked=FALSE` for the target ROI.

**Stage 2 — FocalClassifier**

- **FR-006**: The system MUST implement a `FocalClassifier` class that classifies invasive species using a spectral feature vector of `[ndvi, endvi, red_edge, elevation]`.
- **FR-007**: Elevation values in the feature vector MUST be sourced from the USGS 3DEP API (`https://tnmapi.cr.usgs.gov/api/`) for the prediction point geometry.
- **FR-008**: `FocalClassifier.predict(X)` MUST return `(species_label, confidence)` where `species_label` is a non-empty string and `confidence` is a float.
- **FR-009**: `confidence` MUST be clamped to [0.0, 1.0] before any DB write to satisfy the `invasion_predictions.confidence CHECK` constraint.
- **FR-010**: The `FocalClassifier` model version string MUST be `rf-v0.1.0` as registered in `AGENTS.md` Section 6.
- **FR-011**: The trained model artifact MUST be saved to and loaded from `models/FocalClassifier/rf-v0.1.0/model.joblib`.
- **FR-012**: Training labels for Stage 2 MUST be sourced from `ground_truth_observations` using `species_label` as the target class.
- **FR-013**: For HTTP 429 from USGS 3DEP, the system MUST apply exponential backoff with max 3 retries; on final failure it MUST fall back to `elevation=0.0` and log a warning — it MUST NOT raise an unhandled exception.

**Stage 3 — UNetTexture**

- **FR-014**: The system MUST implement a `UNetTexture` class wrapping a PyTorch U-Net operating on 512×512 image patches.
- **FR-015**: `UNetTexture.infer(patch_tensor)` MUST return a `hotspot_score` float in [0.0, 1.0]; values outside this range MUST be clamped before persistence.
- **FR-016**: The `UNetTexture` model version string MUST be `unet-v0.1.0` as registered in `AGENTS.md` Section 6.
- **FR-017**: The model artifact MUST be loaded from `models/UNetTexture/unet-v0.1.0/model.pt`.
- **FR-017a**: Stage 3 MUST consume a 512x512 four-channel raster patch centered on the Wave 3 detection point for the anomalous scene date; if the source raster window is smaller at scene boundaries, the patch MUST be padded or cropped deterministically to preserve a 512x512 tensor.
- **FR-017b**: The Stage 3 raster patch MUST be sourced from the Planetary Computer STAC item referenced by `spectral_time_series.stac_item` for the anomalous scene date, resolved and signed using `app/services/stac_client.py`. The four channels MUST be Sentinel-2 bands B04 (Red), B08 (NIR), B03 (Green), and B05 (Red-Edge) in that order; all channels MUST be resampled to a common 10m pixel grid before patch extraction. If the STAC asset is unavailable, the pipeline MUST log the failure, skip that candidate, and continue with remaining candidates.

**Pipeline Orchestrator**

- **FR-018**: The system MUST implement `run_pipeline(roi_id)` in `app/services/pipeline.py` that chains Stage 1 → Stage 2 → Stage 3 in strict order for a given ROI.
- **FR-019**: `run_pipeline` MUST write one `InvasionPrediction` row per detected prediction point with all required columns: `roi_id`, `species_label`, `confidence`, `hotspot_score`, `geom` (POINT, SRID 4326), `model_version`, `predicted_at`, `validated=NULL`, `validator_notes=NULL`.
- **FR-020**: `model_version` in `invasion_predictions` MUST store the Stage 2 classifier version string (`rf-v0.1.0`); Stage 1 and Stage 3 versions MUST be emitted to structured logs and included in a per-run sidecar metadata payload, but MUST NOT be written to `model_version`.
- **FR-021**: `run_pipeline` MUST return a summary including `roi_id`, `predictions_created`, `model_version`, and `message`.
- **FR-022**: When an ROI has zero unmasked spectral rows, `run_pipeline` MUST return `predictions_created: 0` without raising an exception.
- **FR-022a**: In Wave 3, each anomalous scene candidate MUST map to exactly one detection point derived from the ROI centroid (`ST_Centroid(regions_of_interest.geom)`) in SRID 4326 unless a later architecture amendment introduces pixel-level localization.

**API Endpoints**

- **FR-023**: The system MUST expose `POST /api/v1/rois/{id}/pipeline/run` that triggers `run_pipeline` for the specified ROI and returns the pipeline summary.
- **FR-024**: `POST /api/v1/rois/{id}/pipeline/run` MUST return `404` when the ROI does not exist.
- **FR-025**: The system MUST expose `GET /api/v1/predictions` that returns a GeoJSON FeatureCollection of `invasion_predictions` rows.
- **FR-026**: `GET /api/v1/predictions` MUST support the following optional query filters: `roi_id` (UUID), `species_label` (string), `validated` (boolean where `true` = confirmed, `false` = rejected, and omitted = no validated-state filter, including NULL/pending rows), `min_hotspot_score` (float).
- **FR-027**: Each GeoJSON Feature in the `GET /api/v1/predictions` response MUST include the following properties: `id`, `roi_id`, `species_label`, `confidence`, `hotspot_score`, `model_version`, `predicted_at`, `validated`.
- **FR-028**: `GET /api/v1/predictions` MUST default to ordering by `hotspot_score DESC` (using `idx_pred_score` index).

### Non-Functional Constraints

- **NFR-001 (Data Integrity)**: All `confidence` values MUST satisfy `0.0 <= confidence <= 1.0` before any DB write; values outside this range MUST be clamped at the service layer.
- **NFR-002 (Data Integrity)**: All `hotspot_score` values MUST satisfy `0.0 <= hotspot_score <= 1.0` before any DB write.
- **NFR-003 (Schema Integrity)**: No new columns or tables are introduced in Wave 3; all writes target the `invasion_predictions` canonical table as defined in `AGENTS.md` Section 4.
- **NFR-004 (Registry Compliance)**: Model version strings in code and DB writes MUST exactly match the registry values in `AGENTS.md` Section 6 — `anomaly-v0.1.0`, `rf-v0.1.0`, `unet-v0.1.0`.
- **NFR-005 (Resilience)**: External API failures (USGS 3DEP HTTP 429) MUST follow the AGENTS failure-mode contract: exponential backoff max 3 retries, then log and use fallback; MUST NOT propagate as unhandled exceptions.
- **NFR-006 (Latency)**: `POST /api/v1/rois/{id}/pipeline/run` SHOULD complete within 120 seconds for an ROI with up to 50 unmasked spectral rows under normal operating conditions.
- **NFR-007 (Determinism)**: Wave 3 detection-point derivation and Stage 3 patch extraction MUST be deterministic for the same ROI geometry and anomalous scene date.

### Key Entities

- **InvasionPrediction** (`invasion_predictions` table): This feature writes new rows. Columns written: `roi_id`, `species_label`, `confidence`, `hotspot_score`, `geom`, `model_version`, `predicted_at`. Columns left at their default: `validated=NULL`, `validator_notes=NULL`. No schema migration is required — the table was created in Wave 1.
- **SpectralTimeSeries** (`spectral_time_series` table): This feature reads rows. Columns consumed: `roi_id`, `scene_date`, `ndvi`, `endvi`, `red_edge`, `is_masked`. No writes to this table.
- **GroundTruthObservation** (`ground_truth_observations` table): Read during Stage 2 training to extract `species_label` values. No writes during inference.

## Architecture

### Data Flow

```
spectral_time_series
  (roi_id, scene_date, ndvi, endvi, red_edge, is_masked)
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Stage 1 — AnomalyDetector (anomaly-v0.1.0)         │
│  IsolationForest on NDVI time series                │
│  Input:  NDVI sequence for ROI (is_masked=FALSE)    │
│  Output: [(scene_date, departure_score), ...]       │
└──────────────────────┬──────────────────────────────┘
                       │  anomalous scene list
                       ▼
         USGS 3DEP elevation lookup
         (per prediction point geometry)
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  Stage 2 — FocalClassifier (rf-v0.1.0)              │
│  RandomForest on spectral feature vector            │
│  Input:  [ndvi, endvi, red_edge, elevation]         │
│  Output: (species_label, confidence)                │
└──────────────────────┬──────────────────────────────┘
                       │  species_label, confidence
                       ▼
┌─────────────────────────────────────────────────────┐
│  Stage 3 — UNetTexture (unet-v0.1.0)                │
│  PyTorch U-Net, 512×512 image patches               │
│  Input:  spatial raster patch centered on the ROI   │
│          centroid for the anomalous scene date      │
│  Output: hotspot_score ∈ [0.0, 1.0]                │
└──────────────────────┬──────────────────────────────┘
                       │  hotspot_score
                       ▼
invasion_predictions
  (species_label, confidence, hotspot_score,
   geom POINT 4326, model_version=rf-v0.1.0,
   validated=NULL)
```

### Model Artifact Paths

| Stage | Class | Version | Artifact Path |
| :--- | :--- | :--- | :--- |
| Stage 1 | `AnomalyDetector` | `anomaly-v0.1.0` | `models/AnomalyDetector/anomaly-v0.1.0/model.joblib` |
| Stage 2 | `FocalClassifier` | `rf-v0.1.0` | `models/FocalClassifier/rf-v0.1.0/model.joblib` |
| Stage 3 | `UNetTexture` | `unet-v0.1.0` | `models/UNetTexture/unet-v0.1.0/model.pt` |

### Stage Contracts

#### Stage 1 — AnomalyDetector (`anomaly-v0.1.0`)

| Property | Value |
| :--- | :--- |
| **Module** | `app/ml/stage1_anomaly.py` |
| **Training script** | `app/scripts/train_anomaly.py` |
| **Input source** | `spectral_time_series` (unmasked rows only: `is_masked=FALSE`) |
| **Input feature** | NDVI sequence ordered by `scene_date` for the target ROI |
| **Training API** | `fit(roi_id, season_start, season_end)` |
| **Inference API** | `predict(roi_id)` |
| **Output** | `List[Tuple[date, float]]` — `(scene_date, departure_score)` for anomalous scenes |
| **Model version** | `anomaly-v0.1.0` |
| **Artifact** | `models/AnomalyDetector/anomaly-v0.1.0/model.joblib` |
| **Training output** | `app/scripts/train_anomaly.py` MUST produce a loadable artifact at the registered path |
| **Lineage capture** | Version emitted to structured log at inference time; NOT written to `invasion_predictions.model_version` |

#### Stage 2 — FocalClassifier (`rf-v0.1.0`)

| Property | Value |
| :--- | :--- |
| **Module** | `app/ml/stage2_classifier.py` |
| **Training script** | `app/scripts/train_classifier.py` |
| **Feature extractor** | `app/services/feature_extractor.py` |
| **Input source** | `spectral_time_series` (ndvi, endvi, red_edge) + USGS 3DEP elevation |
| **Feature vector** | `[ndvi, endvi, red_edge, elevation]` |
| **Training API** | `fit(X, y)` where `y` = `species_label` from `ground_truth_observations` |
| **Inference API** | `predict(X)` |
| **Output** | `Tuple[str, float]` — `(species_label, confidence)` |
| **Confidence range** | Clamped to [0.0, 1.0] before DB write |
| **Model version** | `rf-v0.1.0` |
| **Artifact** | `models/FocalClassifier/rf-v0.1.0/model.joblib` |
| **Training output** | `app/scripts/train_classifier.py` MUST produce a loadable artifact at the registered path |
| **Lineage capture** | This version IS written to `invasion_predictions.model_version` |

#### Stage 3 — UNetTexture (`unet-v0.1.0`)

| Property | Value |
| :--- | :--- |
| **Module** | `app/ml/stage3_unet.py` |
| **Input** | 512×512 spatial raster patch (4-channel tensor) centered on the ROI centroid for the anomalous scene date |
| **Raster source** | Planetary Computer STAC item from `spectral_time_series.stac_item` for the anomalous scene date; signed via `app/services/stac_client.py` |
| **Band mapping (4 channels)** | B04 (Red), B08 (NIR), B03 (Green), B05 (Red-Edge) in that order; all resampled to 10m before windowed extraction |
| **Inference API** | `infer(patch_tensor)` |
| **Output** | `float` — `hotspot_score` clamped to [0.0, 1.0] |
| **Model version** | `unet-v0.1.0` |
| **Artifact** | `models/UNetTexture/unet-v0.1.0/model.pt` |
| **Patch fallback** | Boundary-short patches are padded or cropped deterministically to preserve a 512×512 tensor |
| **Lineage capture** | Version emitted to structured log and included in per-run sidecar metadata; NOT written to `invasion_predictions.model_version` |

## API Endpoints

### `POST /api/v1/rois/{id}/pipeline/run`

**Purpose**: Trigger the full three-stage AI pipeline for the specified ROI.

**Path parameters**:
- `id` (UUID): The ROI to run the pipeline against.

**Response — 200 OK** (pipeline executed, zero or more predictions created):
```json
{
  "roi_id": "uuid",
  "predictions_created": 3,
  "model_version": "rf-v0.1.0",
  "message": "Pipeline completed successfully"
}
```

**Response — 404 Not Found**: ROI does not exist.

**Behaviour**:
- Loads all trained model artifacts before querying the database.
- Runs Stage 1, Stage 2, Stage 3 in strict sequence.
- Returns `predictions_created: 0` when no anomalous scenes are detected or no unmasked spectral data is available — does NOT return a non-2xx status in this case.
- Includes a descriptive `message` explaining whether the run completed with predictions, no anomalies, or no usable spectral input.
- Stage 1 and Stage 3 model versions are written to structured logs and per-run sidecar metadata; only Stage 2's `rf-v0.1.0` appears in the response and in the DB.

---

### `GET /api/v1/predictions`

**Purpose**: Retrieve invasion prediction records as a GeoJSON FeatureCollection, optionally filtered.

**Query parameters** (all optional):

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `roi_id` | UUID | Filter to a specific region of interest |
| `species_label` | string | Exact match filter on species label |
| `validated` | boolean | `true` = confirmed, `false` = rejected; absent = no validated-state filter, including NULL/pending |
| `min_hotspot_score` | float | Include only predictions where `hotspot_score >= value` |

**Response — 200 OK**:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [lon, lat] },
      "properties": {
        "id": "uuid",
        "roi_id": "uuid",
        "species_label": "Bromus tectorum",
        "confidence": 0.87,
        "hotspot_score": 0.74,
        "model_version": "rf-v0.1.0",
        "predicted_at": "2026-03-31T12:00:00Z",
        "validated": null
      }
    }
  ]
}
```

**Ordering**: Results are ordered by `hotspot_score DESC` using the `idx_pred_score` index defined in `AGENTS.md` Section 4.

## Schema Contract

Wave 3 writes to the `invasion_predictions` table as defined in `AGENTS.md` Section 4. **No schema migration is required** — the table and all required columns already exist from Wave 1. Column names and types MUST NOT be altered.

| Column | Type | Wave 3 Write Behaviour |
| :--- | :--- | :--- |
| `id` | UUID | Auto-generated (`gen_random_uuid()`) |
| `roi_id` | UUID FK → `regions_of_interest` | Set from pipeline `roi_id` argument |
| `species_label` | TEXT NOT NULL | Set from Stage 2 output |
| `confidence` | FLOAT NOT NULL CHECK (0.0–1.0) | Set from Stage 2 output, clamped before write |
| `hotspot_score` | FLOAT (nullable) | Set from Stage 3 output, clamped before write |
| `geom` | GEOMETRY(POINT, 4326) NOT NULL | Set from detection point coordinates (WGS84) |
| `model_version` | TEXT NOT NULL | Set to Stage 2 classifier version: **`rf-v0.1.0`** |
| `predicted_at` | TIMESTAMPTZ | Auto-generated (`now()`) |
| `validated` | BOOLEAN (nullable) | Written as `NULL` (pending review) at prediction time |
| `validator_notes` | TEXT (nullable) | Written as `NULL` at prediction time |

**Prediction lineage rule** (per `AGENTS.md` Section 6):
> `invasion_predictions.model_version` stores the Stage 2 classifier version. Stage 1 (`anomaly-v0.1.0`) and Stage 3 (`unet-v0.1.0`) versions MUST be captured in structured pipeline logs and per-run sidecar metadata, but MUST NOT be written to the `model_version` column.

**Wave 3 detection-point contract**:
> Each anomalous scene candidate produces at most one prediction row in Wave 3. The persisted `geom` is the centroid of the ROI polygon in SRID 4326. This keeps the pipeline deterministic until a later wave introduces pixel-level localization.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For an ROI with at least one unmasked `spectral_time_series` row, `POST /api/v1/rois/{id}/pipeline/run` returns `200` and inserts at least one `invasion_predictions` row with a valid `model_version`, `confidence` in [0.0, 1.0], and non-null `geom`.
- **SC-002**: 100% of `invasion_predictions` rows written by the pipeline have `confidence` satisfying the `CHECK (confidence BETWEEN 0.0 AND 1.0)` DB constraint — no constraint-violation errors occur in production runs.
- **SC-003**: 100% of `invasion_predictions` rows written by the pipeline have `hotspot_score` in [0.0, 1.0].
- **SC-004**: `model_version` on every written row equals exactly `rf-v0.1.0` — no other value is acceptable.
- **SC-005**: `GET /api/v1/predictions?roi_id={id}` returns a valid GeoJSON FeatureCollection with all required feature properties for each prediction.
- **SC-006**: Calling `POST /api/v1/rois/{id}/pipeline/run` for an ROI with zero usable spectral rows returns `200` with `predictions_created: 0`, a descriptive `message`, and does not raise an exception.
- **SC-009**: Stage 1 and Stage 3 lineage metadata are emitted for every pipeline run through structured logs and a per-run sidecar metadata payload.
- **SC-007**: USGS 3DEP HTTP 429 failures are handled within the retry budget (≤ 3 retries with exponential backoff); the pipeline continues with `elevation=0.0` fallback without aborting.
- **SC-008**: All three model artifacts load successfully from their registered paths before any DB write occurs; a missing artifact produces a clear error at startup, not a silent data failure.

## Assumptions

- Wave 2 is complete and `spectral_time_series` contains at least one unmasked row for the test ROI used in integration testing.
- Pre-trained model artifacts (`model.joblib` for Stages 1 and 2, `model.pt` for Stage 3) are present at their registry paths at pipeline startup.
- Training scripts (`train_anomaly.py`, `train_classifier.py`) produce serialised artifacts compatible with the inference classes in the same feature wave.
- The detection point `geom` written to `invasion_predictions` is the ROI centroid in Wave 3; pixel-level anomaly localization is explicitly deferred.
- USGS 3DEP elevation lookup is point-in-time; no time-series elevation data is required.
- No Alembic migration is needed for Wave 3 — all required columns in canonical tables already exist.
- AlphaEarth embeddings are NOT used in Wave 3 (see `AGENTS.md` Section 6 benchmark rule).

## Out of Scope

- **HITL validation dashboard** — the `PATCH /api/v1/predictions/{id}/validate` endpoint and Leaflet map are Wave 4 deliverables.
- **Retraining trigger** — the feedback batch collection and `RETRAINING_TRIGGERED` logic are Wave 4 deliverables.
- **AlphaEarth / Earth Engine embeddings** — Wave 1.5 benchmark work; MUST NOT be used as Wave 3 Stage 2 feature inputs.
- **`landsat-hls` and `naip` scene ingestion** — Wave 2 limitation carried forward; Stage 1 only operates on Sentinel-2 NDVI values.
- **Pagination on `GET /api/v1/predictions`** — `LIMIT`/`OFFSET` is a Wave 5 polish item.
- **Schema changes** — no new tables, no new columns, no Alembic migration in this wave.
- **UI rendering** — no Jinja2 templates or HTMX interactions are in scope for Wave 3.

## Dependencies

| Dependency | Required State |
| :--- | :--- |
| Wave 1 complete | `invasion_predictions` and `spectral_time_series` tables exist with canonical schema |
| Wave 2 complete | `spectral_time_series` is populated with at least one unmasked Sentinel-2 row for the integration test ROI |
| USGS 3DEP API | Public endpoint available; no auth required (per `AGENTS.md` Section 5) |
| `scikit-learn` | Available in the `uv`-managed Python environment for IsolationForest and RandomForest |
| `torch` | Available in the environment for U-Net inference |
| `joblib` | Available for model serialisation/deserialisation |
| Model training artifacts | Staged at `models/AnomalyDetector/anomaly-v0.1.0/model.joblib`, `models/FocalClassifier/rf-v0.1.0/model.joblib`, `models/UNetTexture/unet-v0.1.0/model.pt` before pipeline execution |
