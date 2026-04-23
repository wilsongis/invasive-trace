# System Patterns: Invasive Trace

## Architecture Overview
Three-stage AI pipeline backed by a FastAPI + PostGIS service, consumed via REST API and a Leaflet/HTMX dashboard.

```
Planetary Computer STAC
        │
        ▼
[Scene Ingestion Service]  →  spectral_time_series (PostGIS)
        │
        ▼
[Stage 1: AnomalyDetector]  →  IsolationForest / Z-score on NDVI time series
        │  flags anomalous ROIs
        ▼
[Stage 2: FocalClassifier]  →  RandomForest / XGBoost on spectral feature vectors
        │  species_label + confidence
        ▼
[Stage 3: UNetTexture]  →  512×512 patch U-Net → hotspot_score
        │
        ▼
invasion_predictions (PostGIS)
        │
        ▼
[HITL Dashboard]  →  Leaflet map + prediction cards → validate/reject
        │
        ▼
[Retrain Trigger]  →  RETRAINING_TRIGGERED at ≥50 feedback events
```

## Key Design Patterns

### 1. Read-Execute-Write Agent Loop
Before any feature work: read AGENTS.md §4 (schema), §5 (API contracts), §6 (ML registry).
After architectural decisions: update AGENTS.md.

### 2. Graceful Degradation on External APIs
All external consumers (`inat_consumer`, `eddmaps_consumer`, `stac_client`) follow:
- HTTP 429 → exponential backoff, max 3 retries, jitter
- Missing data → log and skip, never raise unhandled
- Cloud-masked scenes (`cloud_cover > 0.20`) → `is_masked=TRUE`, excluded from index computation
- Auth failures (AlphaEarth) → log and skip, never block Planetary Computer baseline

### 3. Deterministic Spatial Fallback
Detection points use ROI centroid as deterministic fallback when no valid pixel coordinate is available. Ensures `invasion_predictions.geom` is never null.

### 4. Schema Contract Lock
Column names and geometry types in `AGENTS.md §4` are locked. Changes require:
1. Alembic migration in `migrations/versions/`
2. AGENTS.md §4 update
3. ORM model update in `app/models/`

### 5. Upsert Pattern
`spectral_time_series` uses `UNIQUE(roi_id, stac_item)` constraint. Scene ingestion uses upsert (INSERT ... ON CONFLICT DO UPDATE) to avoid duplicate scenes.

### 6. Model Lineage
`invasion_predictions.model_version` stores Stage 2 classifier version string only (e.g., `rf-v0.1.0`). Stage 1 and Stage 3 versions are captured in logs/sidecar metadata.

### 7. HTMX Partial Rendering
Dashboard uses HTMX `hx-get` for prediction list updates without full page reload. Templates in `app/templates/partials/` return HTML fragments.

## Component Relationships

| Component | Location | Depends On |
| :--- | :--- | :--- |
| FastAPI app | `app/main.py` | `app/db.py`, `app/config.py` |
| DB layer | `app/db.py` | SQLAlchemy async engine, `DATABASE_URL` env |
| ORM models | `app/models/` | GeoAlchemy2 geometry types |
| Pydantic schemas | `app/schemas/` | ORM models |
| STAC client | `app/services/stac_client.py` | planetary-computer, pystac-client |
| Scene ingestion | `app/services/scene_ingestion.py` | stac_client, cloud_mask, indices |
| Feature extractor | `app/services/feature_extractor.py` | spectral_time_series rows |
| Stage 1 | `app/ml/stage1_anomaly.py` | spectral_time_series |
| Stage 2 | `app/ml/stage2_classifier.py` | feature_extractor, trained `classifier.pkl` |
| Stage 3 | `app/ml/stage3_unet.py` | STAC patch (512×512), trained U-Net weights |
| Pipeline | `app/services/pipeline.py` | Stage 1 → 2 → 3 chain |
| HITL API | `app/api/v1/predictions.py` | invasion_predictions ORM |
| Retrain trigger | `app/services/retrain_trigger.py` | count of validated/rejected predictions |
| Dashboard | `app/api/v1/dashboard.py` + templates | predictions API, Leaflet CDN |

## Critical Implementation Paths

### Scene Ingest → Stage 2 Inference
1. `POST /api/v1/scenes/ingest` → `scene_ingestion.py` → STAC query → COG read → index compute → upsert `spectral_time_series`
2. `POST /api/v1/pipeline/run` → `pipeline.py` → Stage 1 anomaly → Stage 2 classify → Stage 3 score → insert `invasion_predictions`

### HITL Feedback Loop
1. `PATCH /api/v1/predictions/{id}/validate` → update `validated` + `validator_notes`
2. `retrain_trigger.check_retrain_trigger()` — count `WHERE validated IS NOT NULL` → emit log if ≥50

### Model Artifact Path
`./models/{ModelName}/{version}/` — e.g., `./models/FocalClassifier/rf-v0.1.0/classifier.pkl`