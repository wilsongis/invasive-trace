# Quickstart: Stage 2 Focal Classifier

**Feature**: `specs/009-stage2-focal-classifier/`  
**Date**: 2026-04-07  
**Audience**: Implementation team, QA, operational validation

---

## Purpose

Validate Stage 2 training and inference behavior end-to-end using script-driven entrypoints and existing prediction retrieval endpoints.

---

## Prerequisites

### 1. Research Preflight
```bash
just research-sync     # Initialize NotebookLM MCP connection (run once after clone)
just research-test     # Verify MCP connection is live
```

### 2. Local Environment
```bash
just start             # Start Podman container stack (PostgreSQL + FastAPI)
# OR
just run               # Run FastAPI natively with `uv`
```

### 3. Canonical Data Readiness
Verify the following exist in the database:
- ✓ At least 1 region of interest (ROI) with valid SRID 4326 polygon geometry
- ✓ At least 50 spectral_time_series rows with `is_masked = FALSE` (unmasked Sentinel-2 scenes)
- ✓ At least 10 ground_truth_observations with `is_confirmed = TRUE` (confirmed invasive species labels) spanning ≥1 species
- ✓ Spectral time series spanning ≥12 months for reliable feature aggregation

**Quick Check**:
```sql
-- From psql inside PostGIS container
SELECT COUNT(*) FROM regions_of_interest;                           -- expect ≥1
SELECT COUNT(*) FROM spectral_time_series WHERE is_masked = FALSE;  -- expect ≥50
SELECT COUNT(*) FROM ground_truth_observations WHERE is_confirmed = TRUE;  -- expect ≥10
```

---

## Workflow A: Training Stage 2 Artifact

### Step 1: Seed Observations (if needed)
If ground_truth_observations is empty, populate with iNaturalist + EDDMapS:
```bash
just seed-data           # Fetches invasive species observations
```

### Step 2: Train Classifier
```bash
uv run python app/scripts/train_classifier.py \
  --roi-ids ""  \
  --output-dir ./models/FocalClassifier/rf-v0.1.0/
```

**Parameters**:
- `--roi-ids ""` (empty): Auto-detect all ROIs with sufficient data
- `--output-dir`: Must include version in path (e.g., `rf-v0.1.0`)

**Expected Output**:
```json
{
  "status": "success",
  "model_version": "rf-v0.1.0",
  "training_date": "2026-04-07T14:30:00Z",
  "training_sample_count": 1250,
  "cv_f1_macro": 0.516,
  "test_f1_macro": 0.518,
  "test_precision_macro": 0.530,
  "test_recall_macro": 0.510,
  "run_summary": {
    "skipped_invalid_features": 5,
    "skipped_low_scene_count": 2,
    "skipped_unknown_species": 0
  },
  "output_dir": "./models/FocalClassifier/rf-v0.1.0/"
}
```

**Validation Criteria**:
- [ ] Status is `"success"`
- [ ] `test_f1_macro ≥ 0.50` (production threshold per research.md Decision 9)
- [ ] Artifact files exist:
  ```bash
  ls -la models/FocalClassifier/rf-v0.1.0/
  # expect: classifier.pkl, metadata.json, feature_names.txt, class_labels.txt, README.md
  ```
- [ ] metadata.json contains training sample counts and CV metrics:
  ```bash
  cat models/FocalClassifier/rf-v0.1.0/metadata.json | jq '.training_sample_count_by_species'
  ```

---

## Workflow B: Inference with Stage 2 Artifact

### Step 3: Run Inference on ROI(s)
```bash
uv run python app/scripts/run_stage2_inference.py \
  --roi-ids <uuid-of-target-roi> \
  --model-version rf-v0.1.0
```

**Parameters**:
- `--roi-ids`: Required; UUID of ROI (get from `GET /api/v1/rois`)
- `--model-version`: Must match trained artifact directory

**Example**:
```bash
uv run python app/scripts/run_stage2_inference.py \
  --roi-ids "550e8400-e29b-41d4-a716-446655440000" \
  --model-version rf-v0.1.0
```

**Expected Output**:
```json
{
  "status": "success",
  "model_version": "rf-v0.1.0",
  "inference_date": "2026-04-07T15:00:00Z",
  "run_summary": {
    "roi_results": [
      {
        "roi_id": "550e8400-e29b-41d4-a716-446655440000",
        "candidates_generated": 450,
        "candidates_processed": 445,
        "predictions_written": 445,
        "skipped_invalid_features": 5,
        "inference_time_sec": 1.23
      }
    ],
    "total_predictions_written": 445,
    "total_inference_time_sec": 1.23
  }
}
```

**Validation Criteria**:
- [ ] Status is `"success"`
- [ ] `candidates_processed ≈ candidates_generated` (≥99% success rate)
- [ ] `predictions_written > 0` (some predictions persisted)
- [ ] `inference_time_sec < 2.0` (latency budget: <2s per ROI)

---

## Workflow C: Validation via API

### Step 4: Retrieve Predictions
```bash
curl -X GET "http://localhost:8000/api/v1/predictions?roi_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json"
```

**Expected Response** (200 OK):
```json
{
  "predictions": [
    {
      "id": "uuid-pred-1",
      "roi_id": "550e8400-e29b-41d4-a716-446655440000",
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
      "id": "uuid-pred-2",
      "roi_id": "550e8400-e29b-41d4-a716-446655440000",
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
  "total": 445,
  "limit": 100,
  "offset": 0
}
```

**Validation Criteria**:
- [ ] HTTP 200 response
- [ ] `predictions` array non-empty (stage 2 produced outputs)
- [ ] Each prediction has:
  - `species_label` (TEXT, non-empty)
  - `confidence` bounded to [0.0, 1.0]
  - `geom.type` = "Point"
  - `model_version` = "rf-v0.1.0"
  - `validated` = null (pending HITL review)

---

## Workflow D: HITL Validation Feedback (Optional)

### Step 5: Validate a Prediction via Dashboard/API
```bash
curl -X PATCH \
  "http://localhost:8000/api/v1/predictions/uuid-pred-1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "validated": true,
    "validator_notes": "Confirmed invasive Bromus tectorum at field visit 2026-04-05"
  }'
```

**Expected Response** (200 OK):
```json
{
  "id": "uuid-pred-1",
  "validated": true,
  "validator_notes": "Confirmed invasive Bromus tectorum at field visit 2026-04-05",
  "updated_at": "2026-04-07T16:00:00Z"
}
```

**Validation Criteria**:
- [ ] HTTP 200 response
- [ ] `validated` updated to `true` or `false`
- [ ] `validator_notes` persisted

### Step 6: Accumulate Feedback and Trigger Retraining (Future)
Once ≥50 predictions have been validated:
```sql
-- Check retraining trigger status
SELECT COUNT(*) FROM invasion_predictions 
  WHERE model_version = 'rf-v0.1.0' 
    AND validated IS NOT NULL;
-- Expect: ≥50 records triggers next retraining cycle → rf-v0.2.0
```

---

## Workflow E: Resilience Testing (Optional)

### Test: Missing Spectral Data Handling
```bash
# Inject prediction with missing STAC data, confirm skip + log
uv run python app/scripts/run_stage2_inference.py \
  --roi-ids <uuid> \
  --model-version rf-v0.1.0
# Check logs: Should show skipped candidates with reasons
```

**Validation Criteria**:
- [ ] Inference continues despite some candidates failing feature extraction
- [ ] Log output shows skipped counts and reasons
- [ ] Status remains "success" or "partial"

### Test: Expired Model Version Handling
```bash
# Attempt inference with non-existent model version
uv run python app/scripts/run_stage2_inference.py \
  --roi-ids <uuid> \
  --model-version rf-v0.99.0  # Non-existent
```

**Expected Behavior**:
- [ ] Script exits with error message (model artifact not found)
- [ ] No predictions written
- [ ] Error clearly states missing artifact path

---

## Validation Checklist

### Training Validation
- [ ] Training script completes successfully
- [ ] Artifact files written to correct path
- [ ] Metrics logged: sample counts, CV F1, test F1
- [ ] Metadata JSON contains feature names + class labels
- [ ] Serialized classifier can be loaded: `joblib.load(classifier.pkl)`

### Inference Validation
- [ ] Inference script runs without crashes
- [ ] Predictions written to `invasion_predictions` table
- [ ] Confidence values in [0.0, 1.0] range
- [ ] `model_version` = "rf-v0.1.0" for all predictions
- [ ] Geospatial points are valid SRID 4326
- [ ] Total predictions ≈ (1 centroid + grid points) × number of ROIs

### API Validation
- [ ] GET /api/v1/predictions returns valid GeoJSON
- [ ] PATCH /api/v1/predictions/{id}/validate updates validated status
- [ ] No new HTTP endpoints introduced (existing HITL endpoints reused)

### Resilience Validation
- [ ] Partial data failures do not block full inference run
- [ ] Skip logs document reasons for every skipped candidate
- [ ] Error summaries provided in script output
- [ ] Exponential backoff + 3-retry contract honored for external API calls

---

## Performance Baselines

| Operation | Target | Threshold |
|-----------|--------|-----------|
| Training (1000 samples) | 20–30s | <60s |
| Inference per ROI (500 candidates) | 1–2s | <5s |
| Feature extraction per candidate | 50ms | <500ms |
| Prediction write to DB (batch 500) | 500ms | <2s |

**Measurement**:
```bash
# Time training
time uv run python app/scripts/train_classifier.py ...

# Time inference
time uv run python app/scripts/run_stage2_inference.py ...
```

---

## Troubleshooting

### Issue: "No training data found"
- Check ROIs exist and have spectral_time_series rows
- Verify ground_truth_observations has ≥10 confirmed records per species
- Run `just seed-data` to populate ground truth

### Issue: "Model artifact not found"
- Ensure training was completed with correct `--output-dir`
- Check directory exists: `ls ./models/FocalClassifier/rf-v0.1.0/`
- Filename is `classifier.pkl`, not other variants

### Issue: "Confidence values out of range"
- Debug: Check if predictions were clipped to [0.0, 1.0] before INSERT
- Verify DB CHECK constraint: `SELECT * FROM information_schema.table_constraints WHERE table_name='invasion_predictions'`

### Issue: "Predictions not persisted"
- Check database connection: `just db-migrate` should work without errors
- Verify INSERT statements are not being rolled back
- Check logs for SQL errors

---

## Next Steps

1. **Code Implementation**: Use this validation flow to confirm `train_classifier.py` and `run_stage2_inference.py` behavior
2. **Integration Tests**: Capture these steps in `tests/integration/test_stage2_pipeline.py`
3. **Unit Tests**: Test feature extraction, data validation, confidence clipping in isolation
4. **Performance Tuning**: Use baselines above; profile if operations exceed thresholds
5. **Production Deployment**: Wrap training entrypoint in cron job or orchestrator (Wave 5 Polish roadmap)


- Missing/invalid candidate records are skipped, not fatal.
- Elevation lookup failures fallback to 0.0 with warning logs.
- Pipeline still returns success response for partial runs.

## 5) Quality Gate

Run:

just lint
just test
just verify

Expected result:
- No lint errors.
- Tests for Stage 2 training, feature extraction, and pipeline behavior pass.

## Rollback Notes

If regression is detected:
1. Revert Stage 2 code changes in app/ml, app/services, and app/scripts.
2. Restore prior model artifact or retrain with known-good baseline data.
3. Re-run just verify before reopening pipeline runs.
