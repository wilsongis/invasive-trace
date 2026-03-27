---
description: "Invasive Trace — Project-level implementation TODO (wave approach)"
status: active
version: 1.0.0
updated: 2026-03-27
---

# TODO: Invasive Trace

**Source of truth**: `AGENTS.md` — check Sections 4, 5, 6 before touching any task below.
**Execution model**: Waves are strictly ordered (each wave blocks the next). Tasks marked `[P]` within a wave can run in parallel.

## Format: `[ID] [P?] [Pillar] Description`

- **[P]**: Parallelizable within the wave — different files, no shared dependency
- **[PI]** / **[PII]** / **[PIII]** / **[PIV]**: Pillar tag
- All file paths relative to repo root

---

## Wave 0 — Environment Bootstrap
*Blocking gate: nothing in Wave 1+ can start until this wave is complete.*

**Constitution Check before starting:**
- [x] `AGENTS.md` Section 2 NotebookLM ID is populated (`gaia-atlas` / `b22e0bd5-8d0b-4173-a447-2b2442430d6e`)
- [x] `just start` brings up PostGIS + app containers cleanly
- [x] `just lint` passes with zero errors
- [x] `just test` passes with zero errors

**Grounding prerequisites now complete:**
- [x] NotebookLM Dev notebook is configured in project docs and command bridge (`gaia-atlas`)
- [x] `AGENTS.md`, constitution, and `/docs/research/` are internally consistent on review-state semantics (`validated`: `NULL/TRUE/FALSE`)
- [x] Spectral band contract is aligned across plan + research (NDVI: B08/B04, ENDVI: B08/B04/B03, red-edge via Sentinel-2 red-edge bands)
- [x] Prediction lineage rule is aligned across plan + schema (`model_version` stores the Stage 2 classifier version)
- [x] Seed endpoint scope is grounded to a synchronous summary response rather than an undocumented job-status system

### Tasks

- [x] W0-T001 Replace `<REPLACE_WITH_NOTEBOOKLM_ID>` in `AGENTS.md` Section 2 with the real NotebookLM notebook ID
- [x] W0-T002 [P] Scaffold `app/` directory tree: `app/__init__.py`, `app/main.py`, `app/api/__init__.py`, `app/api/v1/__init__.py`, `app/models/__init__.py`, `app/services/__init__.py`, `app/ml/__init__.py`, `app/scripts/__init__.py`
- [x] W0-T003 [P] Create `app/db.py` — async SQLAlchemy engine + `AsyncSession` factory + `get_db` FastAPI dependency
- [x] W0-T004 [P] Create `app/config.py` — Pydantic `Settings` model reading all env vars from `.env` (`DATABASE_URL`, `INAT_API_KEY`, `EDDMAPS_API_KEY`, `PC_SDK_SUBSCRIPTION_KEY`, `LOG_LEVEL`)
- [x] W0-T005 Wire `app/main.py` FastAPI app with lifespan (DB pool open/close), `/healthz` endpoint, and `/api/v1` router include
- [x] W0-T006 [P] Alembic init: `alembic init migrations/`, configure `alembic.ini` and `migrations/env.py` to use `DATABASE_URL` from settings and import all ORM models
- [x] W0-T007 [P] Add `just db-migrate` smoke test to `tests/integration/test_db_connection.py` — assert async DB session returns a row from `pg_stat_activity`
- [x] W0-T008 Validate `just start` launches healthy PostGIS 16-3.4 container; `just db-migrate` runs without error against it
- [x] W0-T009 [P] Connect MCP to gaia-atlas notebook (`just research-sync`), verify with `just research-test`, then upload `/docs/research/` sources manually via the browser (`just research-open`)

**Checkpoint ✓**: Wave 0 complete — `just verify` green (0 lint errors, 8/8 non-integration tests pass), live container start/migrate verified (W0-T008), and research grounding completed (W0-T009).

---

## Wave 1 — Pillar I: Spatial Infrastructure & Seeding
*Depends on: Wave 0 complete.*

**Goal**: Four PostGIS tables created and queryable; ground-truth records seeded from iNaturalist and EDDMapS.

### Phase 1A — PostGIS ORM Models & Migration

- [ ] W1-T001 [P] [PI] Create `app/models/roi.py` — SQLAlchemy `RegionOfInterest` model matching `AGENTS.md` Section 4 DDL exactly (`GEOMETRY(POLYGON, 4326)`, GiST index)
- [ ] W1-T002 [P] [PI] Create `app/models/prediction.py` — `InvasionPrediction` model (`GEOMETRY(POINT, 4326)`, `confidence CHECK 0.0–1.0`, FK to `regions_of_interest`)
- [ ] W1-T003 [P] [PI] Create `app/models/observation.py` — `GroundTruthObservation` model (`source CHECK IN ('iNaturalist','EDDMapS','field_survey')`, `raw_payload JSONB`)
- [ ] W1-T004 [P] [PI] Create `app/models/spectral.py` — `SpectralTimeSeries` model (`platform CHECK IN ('sentinel-2','landsat-hls','naip')`, `is_masked BOOLEAN`)
- [ ] W1-T005 [PI] Autogenerate Alembic migration: `just db-revision msg="create four canonical tables"` — review output, verify geometry columns and all CHECK constraints are present
- [ ] W1-T006 [PI] Apply migration: `just db-migrate` — confirm four tables exist in PostGIS container

### Phase 1B — ROI API Endpoints

- [ ] W1-T007 [P] [PI] Create `app/api/v1/rois.py` router — `POST /api/v1/rois` (create ROI), `GET /api/v1/rois/{id}` (fetch with geometry), `GET /api/v1/rois` (list)
- [ ] W1-T008 [PI] Pydantic schemas in `app/schemas/roi.py` — `ROICreate` (WKT polygon input), `ROIResponse` (GeoJSON geometry output)
- [ ] W1-T009 [P] [PI] Unit test `tests/unit/test_roi_schemas.py` — validate WKT → GeoJSON round-trip serialization
- [ ] W1-T010 [P] [PI] Integration test `tests/integration/test_roi_endpoints.py` — POST creates row, GET returns GeoJSON geometry

### Phase 1C — Ground Truth Seeding (iNaturalist + EDDMapS)

- [ ] W1-T011 [PI] Create `app/services/inat_consumer.py` — async `httpx.AsyncClient` consumer for `https://api.inaturalist.org/v1/observations`; implement exponential backoff (3 retries) on HTTP 429; log + skip on any other failure; write results to `ground_truth_observations`
- [ ] W1-T012 [PI] Create `app/services/eddmaps_consumer.py` — same resilience contract as iNat consumer; write to `ground_truth_observations`
- [ ] W1-T013 [P] [PI] Create `app/scripts/seed_observations.py` — CLI entry point calling both consumers for a configurable taxon list + bounding box; invoked by `just seed-data`
- [ ] W1-T014 [P] [PI] Create `POST /api/v1/observations/sync` endpoint in `app/api/v1/observations.py` — runs the iNaturalist + EDDMapS sync for a given ROI id and returns a summary payload (`sources_polled`, `records_inserted`, `records_skipped`)
- [ ] W1-T015 [P] [PI] Unit test `tests/unit/test_inat_consumer.py` — mock HTTP 429 response; assert backoff is applied and third retry succeeds; assert failure after max retries logs and does not raise
- [ ] W1-T016 [P] [PI] Unit test `tests/unit/test_eddmaps_consumer.py` — same backoff contract test

**Checkpoint ✓**: `just db-migrate` creates four tables; `just seed-data` inserts ≥ 1 observation row; `POST /api/v1/rois` returns 201 with GeoJSON.

---

## Wave 2 — Pillar II: Remote Sensing & Phenology
*Depends on: Wave 1 complete (specifically `regions_of_interest` table + ROI endpoints).*

**Goal**: Sentinel-2 STAC queries running against Planetary Computer; NDVI/ENDVI/Red-Edge indices stored in `spectral_time_series`.

### Phase 2A — STAC Client

- [ ] W2-T001 [PII] Create `app/services/stac_client.py` — async `pystac_client.Client` wrapper for `https://planetarycomputer.microsoft.com/api/stac/v1`; accepts ROI geometry + date range; uses `planetary_computer.sign_inplace` for token refresh; implements graceful skip on missing tiles (log WARN, continue); returns list of valid STAC item hrefs
- [ ] W2-T002 [P] [PII] Unit test `tests/unit/test_stac_client.py` — mock pystac search returning 0 items; assert empty list returned (no exception); mock partial result; assert partial items returned
- [ ] W2-T003 [P] [PII] Integration test `tests/integration/test_stac_query.py` — live query for a known SGI bounding box + recent date range; assert ≥ 1 item returned with `cloud_cover` field present

### Phase 2B — Spectral Index Calculator

- [ ] W2-T004 [PII] Create `app/services/indices.py` — pure functions `compute_ndvi(nir, red)`, `compute_endvi(nir, red, green)`, `compute_red_edge(red_edge_nir, red_edge_red)` — all return `float | None`; raise `ValueError` for mismatched array shapes
- [ ] W2-T005 [P] [PII] Unit test `tests/unit/test_indices.py` — known band values → expected index values (e.g., NDVI = (0.8−0.2)/(0.8+0.2) = 0.6); test None for all-zero denominator

### Phase 2C — Cloud Masking & Ingestion Pipeline

- [ ] W2-T006 [PII] Create `app/services/scene_ingestor.py` — orchestrates: fetch scene via `stac_client`; read COG bands B03 (Green), B04 (Red), B05/B8A (Red-edge), and B08 (NIR) via `rasterio`; compute NDVI, ENDVI, and the chosen red-edge metric; if `cloud_cover > 0.20` persist `is_masked=TRUE` and skip index computation; otherwise persist all three index values to `spectral_time_series`
- [ ] W2-T007 [P] [PII] Create `POST /api/v1/rois/{id}/scenes/ingest` endpoint in `app/api/v1/scenes.py` — accepts `start_date`, `end_date`, triggers `scene_ingestor` for the ROI; returns count of scenes ingested and masked
- [ ] W2-T008 [P] [PII] Unit test `tests/unit/test_scene_ingestor.py` — mock scene with `cloud_cover=0.35`; assert `is_masked=TRUE` persisted and indices are NULL; mock scene `cloud_cover=0.05`; assert indices populated

**Checkpoint ✓**: `POST /api/v1/rois/{id}/scenes/ingest` populates `spectral_time_series` rows; cloud-masked scenes have `is_masked=TRUE` and NULL indices.

---

## Wave 3 — Pillar III: AI Execution Chain
*Depends on: Wave 2 complete (`spectral_time_series` populated for at least one ROI).*

**Goal**: Three-stage ML pipeline producing `invasion_predictions` with hotspot scores.

### Phase 3A — Stage 1: Anomaly Detector

- [ ] W3-T001 [PIII] Create `app/ml/stage1_anomaly.py` — `AnomalyDetector` class wrapping `sklearn.ensemble.IsolationForest`; `fit(roi_id, season_start, season_end)` trains on historical NDVI baseline from `spectral_time_series`; `predict(roi_id)` returns list of `(scene_date, departure_score)` for anomalous scenes; model version string MUST be `anomaly-v0.1.0` from `AGENTS.md` Section 6
- [ ] W3-T002 [P] [PIII] Training script `app/scripts/train_anomaly.py` — saves fitted model to `models/AnomalyDetector/anomaly-v0.1.0/model.joblib`
- [ ] W3-T003 [P] [PIII] Unit test `tests/unit/test_stage1_anomaly.py` — synthetic 12-month NDVI series with one outlier month; assert outlier flagged; assert non-outlier months not flagged

### Phase 3B — Stage 2: Focal Classifier

- [ ] W3-T004 [PIII] Create `app/ml/stage2_classifier.py` — `FocalClassifier` class wrapping `sklearn.ensemble.RandomForestClassifier`; `fit(X, y)` where X is spectral feature vector `[ndvi, endvi, red_edge, elevation]` and y is `species_label`; `predict(X)` returns `(species_label, confidence)`; model version MUST be `rf-v0.1.0`
- [ ] W3-T005 [P] [PIII] Feature extractor `app/services/feature_extractor.py` — assembles feature vector from `spectral_time_series` + USGS 3DEP elevation for a given point geometry
- [ ] W3-T006 [P] [PIII] Training script `app/scripts/train_classifier.py` — uses `ground_truth_observations` as labels; saves model to `models/FocalClassifier/rf-v0.1.0/model.joblib`
- [ ] W3-T007 [P] [PIII] Unit test `tests/unit/test_stage2_classifier.py` — synthetic feature vectors for two species; assert correct label returned; assert `confidence` in [0.0, 1.0]

### Phase 3C — Stage 3: U-Net Hotspot Scorer

- [ ] W3-T008 [PIII] Create `app/ml/stage3_unet.py` — `UNetTexture` class wrapping PyTorch U-Net (512×512 input patches); `infer(patch_tensor)` returns `hotspot_score` float 0–1; model version MUST be `unet-v0.1.0`; model loaded from `models/UNetTexture/unet-v0.1.0/model.pt`
- [ ] W3-T009 [P] [PIII] Unit test `tests/unit/test_stage3_unet.py` — random 512×512×4 tensor input; assert output is a float in [0.0, 1.0]

### Phase 3D — Pipeline Orchestrator & Predictions API

- [ ] W3-T010 [PIII] Create `app/services/pipeline.py` — `run_pipeline(roi_id)` orchestrates all three stages in sequence; writes final `InvasionPrediction` rows to DB with `species_label`, `confidence`, `hotspot_score`, `model_version`, `geom`, where `model_version` stores the Stage 2 classifier version and Stage 1/Stage 3 lineage is emitted to logs or sidecar metadata
- [ ] W3-T011 [P] [PIII] Create `POST /api/v1/rois/{id}/pipeline/run` endpoint in `app/api/v1/pipeline.py` — triggers pipeline; returns count of predictions created
- [ ] W3-T012 [P] [PIII] Create `GET /api/v1/predictions` endpoint — filterable by `roi_id`, `species_label`, `validated`, `min_hotspot_score`; returns GeoJSON FeatureCollection
- [ ] W3-T013 [P] [PIII] Integration test `tests/integration/test_pipeline.py` — seed one ROI + spectral rows; run pipeline; assert `invasion_predictions` table has ≥ 1 row with valid `model_version` and `confidence BETWEEN 0.0 AND 1.0`

**Checkpoint ✓**: `POST /api/v1/rois/{id}/pipeline/run` completes without error; `GET /api/v1/predictions?roi_id={id}` returns ≥ 1 GeoJSON feature.

---

## Wave 4 — Pillar IV: Human-in-the-Loop (HITL) Dashboard
*Depends on: Wave 3 complete (`invasion_predictions` populated).*

**Goal**: Leaflet map dashboard for expert review with confirm/reject workflow and retraining trigger.

### Phase 4A — Validation API

- [ ] W4-T001 [P] [PIV] Create `PATCH /api/v1/predictions/{id}/validate` endpoint in `app/api/v1/predictions.py` — accepts `{"validated": true/false, "validator_notes": "..."}` body; transitions `invasion_predictions.validated` from `NULL` to `TRUE` or `FALSE`, updates `validator_notes`, and returns the updated record
- [ ] W4-T002 [P] [PIV] Unit test `tests/unit/test_validate_endpoint.py` — assert PATCH sets `validated=TRUE` and persists `validator_notes`; assert 404 for unknown ID

### Phase 4B — Retraining Trigger

- [ ] W4-T003 [PIV] Create `app/services/retrain_trigger.py` — queries `invasion_predictions` for count of rows where `validated IS NOT NULL`; if reviewed-row count ≥ 50 emits log message `RETRAINING_TRIGGERED` and returns `True`; otherwise returns `False`
- [ ] W4-T004 [P] [PIV] Wire `retrain_trigger` into the PATCH validate endpoint — check trigger after every validation write
- [ ] W4-T005 [P] [PIV] Unit test `tests/unit/test_retrain_trigger.py` — mock 49 validated rows → assert no trigger; mock 50 rows → assert trigger fires

### Phase 4C — Leaflet Dashboard (HTMX + Jinja2)

- [ ] W4-T006 [PIV] Create `app/templates/base.html` — Tailwind CSS layout; HTMX script tag; Leaflet CSS + JS from CDN
- [ ] W4-T007 [PIV] Create `app/templates/dashboard.html` — extends `base.html`; full-viewport Leaflet map; HTMX sidebar panel for prediction list loaded from `GET /api/v1/predictions`
- [ ] W4-T008 [P] [PIV] Create `app/templates/partials/prediction_card.html` — HTMX partial rendered per prediction; Confirm button → `PATCH /api/v1/predictions/{id}/validate` with `{"validated": true}`; Reject button → same with `{"validated": false}`; both swap back updated card fragment
- [ ] W4-T009 [P] [PIV] Create `GET /` route in `app/api/v1/dashboard.py` — renders `dashboard.html`; serve static assets from `app/static/`
- [ ] W4-T010 [P] [PIV] Create `GET /api/v1/predictions/geojson` endpoint — returns full GeoJSON FeatureCollection for Leaflet `L.geoJSON()` layer initialisation

**Checkpoint ✓**: Dashboard renders at `http://localhost:8000`; predictions appear as map markers; Confirm/Reject updates predict card via HTMX without page reload; retraining trigger log fires at batch 50.

---

## Wave 5 — Polish & Cross-Cutting Concerns
*Depends on: Waves 1–4 complete.*

- [ ] W5-T001 [P] Add structured logging across all service modules — use Python `logging` with JSON formatter; all external API failures logged at WARN level with request context
- [ ] W5-T002 [P] Security hardening — audit all endpoints for path traversal (UUID validation on all `{id}` params); confirm no API keys appear in any log output; verify `confidence` DB CHECK constraint is tested
- [ ] W5-T003 [P] Add `GET /api/v1/rois/{id}/spectral-summary` endpoint — returns time-series stats (min/max/mean NDVI per month) as JSON for charting
- [ ] W5-T004 [P] Performance: add `LIMIT`/`OFFSET` pagination to `GET /api/v1/predictions`; add `hotspot_score DESC` ordering (uses `idx_pred_score` index from schema)
- [ ] W5-T005 Update `docs/research/02-ARCHITECTURE.md` sequence diagram to reflect final implemented data flow
- [ ] W5-T006 Run `just verify` — zero lint errors, zero test failures
- [ ] W5-T007 Update `AGENTS.md` Section 9 (Active Context): move all completed Pillar tasks to `### Completed`; update status line

---

## Dependencies & Execution Order

```
Wave 0 (Bootstrap)
  └─▶ Wave 1 (Pillar I — Spatial)
        └─▶ Wave 2 (Pillar II — Remote Sensing)
              └─▶ Wave 3 (Pillar III — AI Chain)
                    └─▶ Wave 4 (Pillar IV — HITL)
                          └─▶ Wave 5 (Polish)
```

### Parallel Opportunities Within Waves

| Wave | Parallelizable groups |
|:---|:---|
| 0 | T002 scaffold + T003 db.py + T004 config.py + T006 alembic init can all run in parallel |
| 1 | All four ORM models (T001–T004) in parallel; iNat + EDDMapS consumers (T011–T012) in parallel |
| 2 | STAC client + index calculator can be developed in parallel before the ingestor is assembled |
| 3 | Stage 1, Stage 2, Stage 3 training scripts can be developed in parallel; API endpoints in parallel |
| 4 | Validation API + retrain trigger + dashboard HTML can be developed in parallel |
| 5 | All polish tasks are fully parallel |

---

## Progress Tracker

| Wave | Status | Blocking? |
|:---|:---|:---|
| Wave 0 — Bootstrap | 🟡 In Progress (grounding complete, runtime bootstrap pending) | Blocks all |
| Wave 1 — Pillar I | ⬜ Not started | Blocks Wave 2+ |
| Wave 2 — Pillar II | ⬜ Not started | Blocks Wave 3+ |
| Wave 3 — Pillar III | ⬜ Not started | Blocks Wave 4+ |
| Wave 4 — Pillar IV | ⬜ Not started | Blocks Wave 5 |
| Wave 5 — Polish | ⬜ Not started | — |

*Update status to 🟡 In Progress / ✅ Complete as waves are worked.*
