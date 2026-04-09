# API Contract: Stage 2 Classifier

**Feature**: `specs/009-stage2-focal-classifier/`  
**Version**: 1.0  
**Date**: 2026-04-07  
**Audience**: Stage 2 implementation team, Stage 3 consumers, HITL dashboard

---

## Overview

Stage 2 classifier is invoked via script-driven training (`app/scripts/train_classifier.py`) and persists predictions to the canonical `invasion_predictions` table. The existing `/api/v1/predictions` endpoint (from Wave 4 HITL dashboard) retrieves and validates Stage 2 outputs; no new HTTP endpoints are introduced.

**Rationale** (research.md Decision 7): Script-driven training is operationally simpler; HTTP endpoints deferred until operational automation requires them.

---

## Stage 2 Training Entrypoint

### Script: `app/scripts/train_classifier.py`

**Invocation**:
```bash
uv run python app/scripts/train_classifier.py \
  --roi-ids <uuid1,uuid2,...> \
  --output-dir ./models/FocalClassifier/rf-v0.1.0/ \
  [--force-retrain]
```

**Name**: `train_classifier.py`

**Parameters**:
- `--roi-ids` (optional): Comma-separated ROI UUIDs to train on (e.g., `uuid1,uuid2`)
  - If omitted: Use all ROIs with ≥10 ground truth observations per target species
- `--output-dir` (required): Path to write model artifact (must include version, e.g., `./models/FocalClassifier/rf-v0.1.0/`)
- `--force-retrain` (optional): Re-train even if existing model exists

**Behavior**:
1. Query `training_cohort` from DB (deterministic, stratified by species)
2. Validate cohort: min 10 observations per species, min 3 scenes per observation
3. Fit RandomForest with `class_weight='balanced'`, `n_estimators=100`, `max_depth=15`, `min_samples_leaf=5`
4. 5-fold stratified cross-validation + test-set evaluation
5. Write `classifier.pkl`, `metadata.json`, `feature_names.txt`, `class_labels.txt` to `--output-dir`
6. Log summary: sample counts, CV F1-macro, test metrics, error counts

**Return Value** (to stdout/stderr):
```json
{
  "status": "success" | "failure",
  "model_version": "rf-v0.1.0",
  "training_date": "2026-04-07T14:30:00Z",
  "training_sample_count": 1250,
  "cv_f1_macro_mean": 0.516,
  "cv_f1_macro_std": 0.023,
  "test_f1_macro": 0.518,
  "test_precision_macro": 0.530,
  "test_recall_macro": 0.510,
  "test_balanced_accuracy": 0.523,
  "run_summary": {
    "skipped_invalid_features": 15,
    "skipped_low_scene_count": 8,
    "skipped_unknown_species": 2
  },
  "output_dir": "./models/FocalClassifier/rf-v0.1.0/"
}
```

---

## Stage 2 Inference Entrypoint

### Script: `app/scripts/run_stage2_inference.py`

**Invocation**:
```bash
uv run python app/scripts/run_stage2_inference.py \
  --roi-ids <uuid1,uuid2,...> \
  --model-version rf-v0.1.0 \
  [--dry-run]
```

**Parameters**:
- `--roi-ids` (required): Comma-separated ROI UUIDs for inference
- `--model-version` (required): Model version string (must exist in `./models/FocalClassifier/{version}/`)
- `--dry-run` (optional): Generate candidates + feature vectors but do NOT persist predictions

**Behavior**:
1. Load classifier from `./models/FocalClassifier/{model_version}/classifier.pkl`
2. For each ROI:
   a. Generate `CandidateLocation` set (centroid + 500m grid)
   b. For each candidate:
      - Extract `Stage2InferenceVector` from spectral time series
      - Skip if <3 unmasked scenes or non-finite features
      - Predict species + confidence via `classifier.predict()` + `classifier.predict_proba()`
      - Clip confidence to [0.0, 1.0]
   c. Persist predictions to `invasion_predictions` table
      - `model_version` = provided version string
      - `validated` = NULL (pending HITL review)
3. Log summary: candidates processed, predictions written, skipped records (with reasons)

**Return Value** (to stdout/stderr):
```json
{
  "status": "success" | "partial" | "failure",
  "model_version": "rf-v0.1.0",
  "inference_date": "2026-04-07T15:00:00Z",
  "run_summary": {
    "roi_results": [
      {
        "roi_id": "uuid-1",
        "candidates_generated": 450,
        "candidates_processed": 445,
        "predictions_written": 445,
        "skipped_invalid_features": 5,
        "inference_time_sec": 1.23
      },
      {
        "roi_id": "uuid-2",
        "candidates_generated": 380,
        "candidates_processed": 378,
        "predictions_written": 378,
        "skipped_invalid_features": 2,
        "inference_time_sec": 0.98
      }
    ],
    "total_predictions_written": 823,
    "total_inference_time_sec": 2.21
  }
}
```

---

## Existing Prediction Retrieval Endpoint

### Endpoint: `GET /api/v1/predictions`

**Source**: Wave 4 HITL Dashboard (existing, no changes required)

**Query Parameters**:
- `roi_id` (optional): Filter by ROI UUID
- `model_version` (optional): Filter by model version (e.g., `rf-v0.1.0`)
- `validated` (optional): Filter by validation state (`null`, `true`, `false`)
- `limit` (optional): Maximum results (default 100)
- `offset` (optional): Pagination offset (default 0)

**Response**:
```json
{
  "predictions": [
    {
      "id": "uuid-1",
      "roi_id": "uuid-roi-1",
      "species_label": "Bromus tectorum",
      "confidence": 0.87,
      "hotspot_score": null,
      "geom": {
        "type": "Point",
        "coordinates": [-104.5, 39.8]
      },
      "model_version": "rf-v0.1.0",
      "predicted_at": "2026-04-07T15:00:00Z",
      "validated": null,
      "validator_notes": null
    },
    {
      "id": "uuid-2",
      "roi_id": "uuid-roi-1",
      "species_label": "Tamarix ramosissima",
      "confidence": 0.62,
      "hotspot_score": null,
      "geom": {
        "type": "Point",
        "coordinates": [-104.52, 39.82]
      },
      "model_version": "rf-v0.1.0",
      "predicted_at": "2026-04-07T15:00:00Z",
      "validated": null,
      "validator_notes": null
    }
  ],
  "total": 2,
  "limit": 100,
  "offset": 0
}
```

---

## HITL Validation Endpoint

### Endpoint: `PATCH /api/v1/predictions/{id}/validate`

**Source**: Wave 4 HITL Dashboard (existing, no changes required)

**Request Body**:
```json
{
  "validated": true,
  "validator_notes": "Confirmed invasive Bromus tectorum at field visit 2026-04-05"
}
```

**Response** (200 OK):
```json
{
  "id": "uuid-1",
  "validated": true,
  "validator_notes": "Confirmed invasive Bromus tectorum at field visit 2026-04-05",
  "updated_at": "2026-04-07T16:00:00Z"
}
```

**Side Effects**:
- Update `invasion_predictions.validated` and `validator_notes`
- On batch ≥50 records with `validated IS NOT NULL`: log message "RETRAINING_TRIGGERED" to indicate next training cycle candidate

---

## Data Contracts (Input/Output Schemas)

### TrainingCohort Schema (Output from query)
```python
@dataclass
class TrainingCohortRecord:
    record_id: UUID
    roi_id: UUID
    species_label: str                    # from ground_truth_observations
    observation_date: date
    ndvi_min: float
    ndvi_max: float
    ndvi_mean: float
    ndvi_std: float
    endvi_min: float
    endvi_max: float
    endvi_mean: float
    endvi_std: float
    red_edge_min: float
    red_edge_max: float
    red_edge_mean: float
    red_edge_std: float
    scene_count: int
```

### InferenceVector Schema (Runtime input)
```python
@dataclass
class InferenceVector:
    candidate_id: UUID
    roi_id: UUID
    features: ndarray  # shape (12,)
    scene_count: int
    # features ordering matches feature_names.txt from model artifact
```

### PredictionOutput Schema
```python
@dataclass
class PredictionOutput:
    candidate_id: UUID
    roi_id: UUID
    species_label: str                    # from classifier.predict()
    confidence: float                     # from classifier.predict_proba(), clipped to [0.0, 1.0]
    geom: Point                          # SRID 4326
    model_version: str                   # = "rf-v0.1.0"
    predicted_at: datetime
    validated: Optional[bool]            # NULL
    validator_notes: Optional[str]       # NULL
```

---

## Error Handling

**Training Errors**:
- Insufficient training data (<10 obs per species): Skip ROI, log warning
- Invalid features (NaN, infinite): Skip record, log warning
- Classifier training failure: Log error, exit with status=-1

**Inference Errors**:
- Model artifact missing: Fail with clear error message
- Invalid candidate location: Skip, log warning
- Feature extraction failure: Skip candidate, log warning
- Non-finite prediction: Clip to [0.0, 1.0], persist with warning log

**External API Errors** (Constitution V):
- HTTP 429 (rate limit): Exponential backoff (3 retries), then skip record
- Missing STAC tile: Skip record, log warning
- Cloud-masked scene: Mark `is_masked=TRUE`, exclude from feature computation

---

## Resilience Guarantees

**Training**:
- Partial cohort (some records invalid): Continue with valid records; log summary
- Complete cohort failure: Exit with error code; retain previous model artifact
- External fetch transient error: Retry exponentially; skip on exhaustion

**Inference**:
- Partial ROI (some candidates fail): Continue with remaining candidates; log summary
- Complete ROI failure: Log error; move to next ROI
- External fetch transient error: Retry exponentially; skip candidate on exhaustion

---

## Versioning & Backward Compatibility

**Current Version**: `rf-v0.1.0` (per AGENTS.md Section 6)

**Future Versions**: 
- `rf-v0.2.0` after successful HITL retraining batch (≥50 validated predictions)
- Both versions coexist on disk; `invasion_predictions.model_version` tracks which was used

**No Breaking Changes to Existing Endpoints**: 
- `/api/v1/predictions/{id}/validate` remains unchanged
- Stage 2 outputs use existing `invasion_predictions` schema (no migration required)

