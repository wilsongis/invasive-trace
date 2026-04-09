# Implementation Plan: Stage 2 Focal Classifier and Feature Extraction

**Branch**: `009-stage2-focal-classifier` | **Date**: 2026-04-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-stage2-focal-classifier/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

**Primary Requirement**: Implement Stage 2 classifier that transforms ROI-linked spectral time series and confirmed ground truth observations into species-level predictions with confidence scores, enabling downstream Stage 3 texture-based hotspot scoring and HITL validation workflows.

**Technical Approach** (from research):
- Train RandomForest / XGBoost focal species classifier on spectral feature vectors (NDVI, ENDVI, Red-Edge indices from `spectral_time_series`) joined to confirmed species labels from `ground_truth_observations`
- Generate deterministic candidate locations (ROI centroids + buffered grid) as inference points
- Extract per-location spectral features from ingested time series (excluding cloud-masked scenes)
- Produce species predictions with confidence scores and Stage 2 model version lineage for persistence to `invasion_predictions`
- Implement resilient external API handling: Planetary Computer STAC queries use exponential backoff (3 retries), graceful skip on missing tiles/cloud-masked records, continuation on partial results
- Capture run-level metadata for reproducibility and audit: processed record counts, skip reasons, generation timestamps, classifier version

## Technical Context

<!-- Stack is LOCKED — do not change these values without a constitution amendment. -->

**Language/Version**: Python 3.12 (managed by `uv`)
**Primary Dependencies**: FastAPI, SQLAlchemy (async) + GeoAlchemy2, scikit-learn (RandomForest/XGBoost), Rasterio, pystac-client, planetary-computer
**Storage**: PostgreSQL 16 + PostGIS 3.4 — reads from `ground_truth_observations`, `spectral_time_series`, `regions_of_interest`; writes to `invasion_predictions`
**Testing**: `pytest` + `pytest-asyncio` via `just test`, Ruff linting via `just lint`
**Target Platform**: Podman-containerized Linux (macOS dev via `just run`)
**Project Type**: Geospatial AI web service (Stage 2 ML pipeline)
**Performance Goals**: Inference < 2s per ROI (500 candidate points); STAC queries < 5s for 1-year time range (research.md Decision 11)
**Constraints**: COG-native raster reads; all geometries SRID 4326; confidence bounded 0.0–1.0 at DB layer; API keys from env vars only; cloud_cover > 0.20 excluded from feature computation; exponential backoff (3 retries) for Planetary Computer queries
**Scale/Scope**: Multi-ROI execution; candidate locations derived from ROI centroids and spatial grid sampling; spectral indices from Sentinel-2 L2A via Planetary Computer STAC

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **PASS** (All checks verified against AGENTS.md Sections 4, 5, 6 and Constitution v2.1.0)

- [x] **Anti-Context Rot (II)**: Verified `AGENTS.md` Section 4 (schema: `invasion_predictions` writes, `spectral_time_series` + `ground_truth_observations` reads), Section 5 (Planetary Computer STAC endpoint, iNaturalist, EDDMapS, exponential backoff rules), Section 6 (Stage 2 model = `FocalClassifier`, version `rf-v0.1.0`).
- [x] **Tech Stack (III)**: Feature uses only mandated stack — FastAPI, uv, PostgreSQL+PostGIS, SQLAlchemy async+GeoAlchemy2, scikit-learn (RandomForest/XGBoost), pystac-client, Rasterio, Ruff. No prohibited tech (TensorFlow, MongoDB, Django, Docker).
- [x] **Spatial Integrity (IV)**: No new schema changes required for Stage 2 (writes to existing `invasion_predictions` table). All geometries SRID 4326. Confidence CHECK constraint (0.0–1.0) preserved in `invasion_predictions`. Alembic migrations only updated if signature changes needed.
- [x] **API Resilience (V)**: All external calls (Planetary Computer STAC, iNaturalist, EDDMapS) implement exponential backoff (3 retries per Constitution V), graceful skip on missing tiles, cloud_cover > 0.20 marked is_masked=TRUE and excluded from feature computation. API keys sourced from env vars only.
- [x] **ML Registry (VI)**: Stage 2 references exact version `rf-v0.1.0` from `AGENTS.md` Section 6. Model artifacts stored at `./models/FocalClassifier/rf-v0.1.0/`. `invasion_predictions.model_version` = `rf-v0.1.0` for all Stage 2 outputs.

## Project Structure

### Documentation (this feature)

```text
specs/009-stage2-focal-classifier/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - executable task list)
```

### Source Code (repository root)

```text
app/
├── api/v1/
│   └── [no changes — existing /api/v1/predictions infrastructure from Wave 4 used for model retrieval]
├── models/
│   ├── base.py            # Existing
│   └── [no changes]
├── ml/
│   ├── stage2_classifier.py    # MODIFY: RandomForest/XGBoost training + inference
│   └── [existing stage 1, 3]
├── services/
│   ├── stac_client.py          # EXISTING: Planetary Computer queries with backoff
│   ├── indices.py              # EXISTING: NDVI/ENDVI/Red-Edge computation
│   ├── feature_extractor.py    # NEW: Spectral feature → training vector extraction
│   └── [existing seed/consumers]
└── scripts/
    ├── train_classifier.py      # NEW: Entrypoint for Stage 2 training
    └── [existing seed, train_anomaly]

tests/
├── unit/
│   ├── test_stage2_classifier.py  # NEW: Training + inference unit tests
│   └── test_feature_extractor.py  # NEW: Feature extraction unit tests
├── integration/
│   └── test_stage2_pipeline.py    # NEW: End-to-end ROI training/inference
└── [existing tests]

models/
└── FocalClassifier/
    └── rf-v0.1.0/
        ├── classifier.pkl  # Trained RandomForest/XGBoost
        ├── metadata.json   # Training cohort info, feature names, class labels
        └── README.md       # Model card: training date, performance metrics
```

**Structure Decision**: Stage 2 extends the existing `app/ml/` and `app/services/` layers. Training pipeline (feature extraction → classifier training) lives in `stage2_classifier.py` and invoked via script entrypoints (`train_classifier.py`, `run_stage2_inference.py`); no new HTTP endpoints per research.md Decision 7. Feature extraction decoupled into `services/feature_extractor.py` for reuse in both training and inference paths. Model artifacts stored with metadata in `./models/FocalClassifier/rf-v0.1.0/` per AGENTS.md Section 6.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
