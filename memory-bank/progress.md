# Progress: Invasive Trace

## What Works (Completed)

### Pillar I Bootstrap (Wave 0) ✅
- FastAPI app scaffold: `app/api/`, `app/models/`, `app/services/`
- `app/config.py` — pydantic-settings runtime config
- `app/db.py` — async SQLAlchemy engine + `get_db` dependency
- `app/main.py` — FastAPI with lifespan, `/healthz`, bootstrap v1 router
- Alembic async migration chain: `alembic.ini`, `migrations/env.py`, `0001_baseline.py`
- Podman compose hardened (bind-mount no longer masks Linux virtualenv)

### Pillar I: Spatial Infrastructure (Wave 1) ✅
- Alembic migration `0002_wave1_canonical_spatial_tables` for all 4 PostGIS tables
- ORM models: `regions_of_interest`, `invasion_predictions`, `ground_truth_observations`, `spectral_time_series`
- ROI API endpoints: `POST /api/v1/rois`, `GET /api/v1/rois/{id}`, `GET /api/v1/rois`
- Ground truth consumers: `inat_consumer.py`, `eddmaps_consumer.py`
- Seed script: `seed_observations.py` → `just seed-data`
- Seed endpoint: `POST /api/v1/observations/sync`
- Phase 6 hardening: retry constants with jitter/budget, sync audit logging, `just seed-data-dry-run`

### Wave 1.5: AlphaEarth Benchmark Spike ✅ (No-Go Decision)
- Benchmark scaffolding implemented and executed
- Result: baseline RF F1=0.4373 vs AlphaEarth F1=0.3750 (delta=-0.0623)
- **Decision: Do NOT adopt AlphaEarth for production Stage 2**
- Report: `docs/research/alphaearth-benchmark-report.md`

### Pillar II: Remote Sensing (Wave 2 / spec 005) ✅
- Migration `0003_spectral_upsert_constraint` — `UNIQUE(roi_id, stac_item)`
- `stac_client.py` — Planetary Computer STAC query + URL signing
- `cloud_mask.py` — QA60 cloud fraction + `is_masked` flag
- `indices.py` — NDVI / ENDVI / Red-Edge CIre computation
- `scene_ingestion.py` — pipeline orchestrator + upsert
- API: `POST /api/v1/scenes/ingest`, `GET /api/v1/scenes`
- Quality gate: 0 lint errors, 0 test failures

### Pillar III: AI Execution Chain (Wave 3 / spec 007) ✅
- Full Stage 1 → 2 → 3 pipeline in `app/services/pipeline.py`
- `stage1_anomaly.py` — IsolationForest / Z-score on NDVI
- `stage2_classifier.py` — RandomForest / XGBoost focal classifier
- `stage3_unet.py` — U-Net texture → hotspot score
- Deterministic ROI-centroid detection fallback
- 512×512 patch STAC extraction for Stage 3
- `POST /api/v1/pipeline/run` endpoint
- Quality gate: ruff clean; pytest 103 passed, 2 skipped

### Stage 2 Focal Classifier (spec 009) ✅
- `models/FocalClassifier/rf-v0.1.0/` artifact directory
- `feature_extractor.py` with `retry_with_backoff`
- `train_classifier.py` — RF + cross-validation + metrics
- `run_stage2_inference.py` CLI script
- US2 Resilience: feature vector validation, cloud mask enforcement, retry logic
- US3 Auditability: deterministic behavior, metadata serialization, model version constant
- Quality gate: ruff clean, 135 passed / 2 skipped

### Pillar IV: HITL Dashboard (Wave 4 / spec 008) ✅
- `PATCH /api/v1/predictions/{id}/validate` endpoint
- `retrain_trigger.py` — `check_retrain_trigger()` with `RETRAIN_THRESHOLD = 50`
- Leaflet + HTMX dashboard: `base.html`, `dashboard.html`, `prediction_card.html`
- Unit tests: `test_validate_endpoint.py` (7), `test_retrain_trigger.py` (5)
- Quality gate: 0 lint errors, 89 passed, 2 skipped

---

## What's Left to Build

### Wave 5: SGI Enhancements (spec 010 authored; specs 011–014 pending)

| Spec | Feature | Status | Dependency |
| :--- | :--- | :--- | :--- |
| 011 | Canopy Height Integration (Meta data) | 📋 Spec pending | None |
| 012 | Woody Pressure Quantification (WPI) | 📋 Spec pending | spec 011 |
| 013 | Invasive Species Catalog (25 states) | 📋 Spec pending | None |
| 014 | Pilot County Selection (TIGER/Line) | 📋 Spec pending | None |

### Backlog
- Stage 3: U-Net model training (currently stub/synthetic)
- Stage 2: Focal classifier training on real SGI data (currently synthetic cohort)
- Stage 1: AnomalyDetector training on real spectral time series
- Wave 5 Polish (general UX + performance hardening)

---

## Current Status
**Quality gate:** ruff clean, 135 passed / 2 skipped (last verified on spec 009 completion)
**Alembic chain:** 0001 → 0002 → 0003 → 0004
**Active branch:** main (post spec 009 merge)
**AGENTS.md version:** v2.8

---

## Known Issues
- DB integration tests require a running PostGIS container — excluded from native `just test` runs
- NotebookLM `just research-sync` requires manual Google login in browser (known limitation, not a blocker)
- AlphaEarth `EE_PROJECT_ID` env var required for Earth Engine benchmark; clean skip on auth failure
- "Montgomery County, YN" pilot county interpreted as Tennessee (TN) — needs SGI confirmation if incorrect

---

## Evolution of Key Decisions

| Decision | Outcome | Date |
| :--- | :--- | :--- |
| AlphaEarth for Stage 2 | **No-go** — lower F1 than baseline RF | Wave 1.5 |
| Canopy height ingestion strategy | **Pre-cache** per SGI ROI (not on-demand) | 2026-04-21 SGI meeting |
| Woody encroachment threshold | **8 ft (2.44m)** canopy height | 2026-04-21 SGI meeting |
| Pilot counties | Montgomery TN, Cherokee GA, Forsyth GA | 2026-04-21 SGI meeting |
| Species catalog scope | 25 states (TX–CT southern/eastern corridor) | 2026-04-21 SGI meeting |
| Ground truth filters | **Hold** — existing implementation sufficient for now | 2026-04-21 SGI meeting |