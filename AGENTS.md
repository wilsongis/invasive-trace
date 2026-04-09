# AGENTS.md: Invasive Trace

> **Single Source of Truth** — Read this before every task. Write to this after every architectural decision.

## 1. Project Identity
**Objective:** Detect, classify, and map invasive plant species across Southern Grassland Institute study areas using multi-temporal remote sensing, spectral analysis, and a three-stage AI execution chain.
**Client:** Southern Grassland Institute
**Status:** Implementation Phase — Waves 0, 1, Pillar II (Remote Sensing), Wave 3 (AI Execution Chain), and Wave 4 (HITL Dashboard) complete; Wave 5 (Polish) in backlog.

---

## 2. Research & Grounding
- **Notebook Name:** "gaia-atlas"
- **Notebook ID:** `b22e0bd5-8d0b-4173-a447-2b2442430d6e`
- **MCP Provider:** AntiGravity / notebooklm-mcp
- **Local Source Set:** `/docs/research/`
- **Primary (Dev):** `just research-sync`
- **Secondary (Prod):** `just notebook=prod research-sync`

**Rule:** Always use the Dev notebook for experimental features. Use `just research-sync` to initialize the MCP connection, `just research-test` to verify it, and upload `/docs/research/` sources through the NotebookLM UI. Only initialize the Prod notebook once an SRS pillar is finalized.

---

## 3. Global Tech Stack (The Standard)

| Layer | Technology | Constraint |
| :--- | :--- | :--- |
| **Backend** | FastAPI + Python 3.12 | No Django/Flask |
| **Database** | PostgreSQL 16 + PostGIS 3.4 | No SQLite/MongoDB |
| **ORM / Spatial** | SQLAlchemy (async) + GeoAlchemy2 | Strictly typed geometries |
| **Frontend** | Jinja2 + HTMX + Tailwind CSS | No React/Vue/Svelte |
| **Raster I/O** | Rasterio + GDAL (via Containerfile) | COG-native reads only |
| **Remote Sensing** | pystac-client + planetary-computer; Google Earth Engine AlphaEarth embeddings (benchmark-only) | Planetary Computer STAC remains the production baseline |
| **ML: Classical** | Scikit-learn (RandomForest / XGBoost) | Spectral feature vectors |
| **ML: Deep** | PyTorch (U-Net architecture) | Spatial texture classification |
| **Package Mgr** | `uv` (strictly) | No pip/poetry |
| **Container** | Podman + Containerfile | No Docker Desktop |
| **Automation** | `just` | No Makefile |
| **Linting** | Ruff | No flake8/black/pylint |

---

## 4. PostGIS Schema (Canonical)

> ⚠️ **Contract Lock**: Do NOT alter column names or geometry types without a schema migration and an AGENTS.md update.

### `regions_of_interest`
```sql
CREATE TABLE regions_of_interest (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    description TEXT,
    geom        GEOMETRY(POLYGON, 4326) NOT NULL,  -- WGS84 polygon
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_roi_geom ON regions_of_interest USING GIST (geom);
```

### `invasion_predictions`
```sql
CREATE TABLE invasion_predictions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roi_id          UUID REFERENCES regions_of_interest(id) ON DELETE CASCADE,
    species_label   TEXT NOT NULL,           -- e.g. "Bromus tectorum"
    confidence      FLOAT NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    hotspot_score   FLOAT,                   -- Stage 3 ecological spread risk (0–1)
    geom            GEOMETRY(POINT, 4326) NOT NULL,
    model_version   TEXT NOT NULL,           -- Stage 2 classifier version, e.g. "rf-v0.1.0"
    predicted_at    TIMESTAMPTZ DEFAULT now(),
    validated       BOOLEAN,                 -- NULL=pending review, TRUE=confirmed, FALSE=rejected
    validator_notes TEXT
);
CREATE INDEX idx_pred_geom   ON invasion_predictions USING GIST (geom);
CREATE INDEX idx_pred_roi    ON invasion_predictions (roi_id);
CREATE INDEX idx_pred_score  ON invasion_predictions (hotspot_score DESC);
```

### `ground_truth_observations`
```sql
CREATE TABLE ground_truth_observations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source        TEXT NOT NULL CHECK (source IN ('iNaturalist', 'EDDMapS', 'field_survey')),
    external_id   TEXT,                      -- Original source record ID
    species_label TEXT NOT NULL,
    observer      TEXT,
    observed_at   DATE,
    geom          GEOMETRY(POINT, 4326) NOT NULL,
    is_confirmed  BOOLEAN DEFAULT TRUE,
    raw_payload   JSONB                      -- Full API response preserved
);
CREATE INDEX idx_gto_geom    ON ground_truth_observations USING GIST (geom);
CREATE INDEX idx_gto_source  ON ground_truth_observations (source);
```

### `spectral_time_series`
```sql
CREATE TABLE spectral_time_series (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roi_id      UUID REFERENCES regions_of_interest(id) ON DELETE CASCADE,
    scene_date  DATE NOT NULL,
    platform    TEXT NOT NULL CHECK (platform IN ('sentinel-2', 'landsat-hls', 'naip')),
    stac_item   TEXT NOT NULL,               -- STAC item ID from Planetary Computer
    ndvi        FLOAT,
    endvi       FLOAT,
    red_edge    FLOAT,                       -- Red Edge Chlorophyll Index
    cloud_cover FLOAT,                       -- Scene-level cloud fraction (QA60)
    is_masked   BOOLEAN DEFAULT FALSE        -- True if cloud-masked out
);
CREATE INDEX idx_sts_roi_date ON spectral_time_series (roi_id, scene_date DESC);
```

---

## 5. API Contracts (External)

| Service | Endpoint | Auth | Usage |
| :--- | :--- | :--- | :--- |
| **Microsoft Planetary Computer** | `https://planetarycomputer.microsoft.com/api/stac/v1` | Token (planetary-computer lib) | Sentinel-2 L2A, Landsat HLS, NAIP queries |
| **Google Earth Engine / AlphaEarth** | `https://earthengine.googleapis.com/` | Google Cloud / Earth Engine auth; requester-pays GCS if export path is used | Benchmark-only annual embedding access for `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` |
| **iNaturalist** | `https://api.inaturalist.org/v1/observations` | API Key (env: `INAT_API_KEY`) | Ground truth seeding; taxon filter by invasive list |
| **EDDMapS** | `https://www.eddmaps.org/api/` | API Key (env: `EDDMAPS_API_KEY`) | Regional occurrence records |
| **USGS 3DEP** | `https://tnmapi.cr.usgs.gov/api/` | None (public) | Elevation context for topographic modelling |

**Failure Modes — All external API consumers MUST handle:**
- HTTP 429 (rate limit): exponential backoff, max 3 retries
- Missing tiles / partial STAC results: log and skip, never raise unhandled
- Cloud-masked scenes (`cloud_cover > 0.20`): mark `is_masked=TRUE`, exclude from index computation
- AlphaEarth auth, coverage, or export failures: log and skip the benchmark run; never block the Planetary Computer baseline workflow
- AlphaEarth annual embeddings MUST NOT be used for Stage 1 temporal anomaly detection unless a separate architecture amendment explicitly approves it

**Sentinel-2 band contract for spectral work:**
- NDVI: B08 (NIR) + B04 (Red)
- ENDVI: B08 (NIR) + B04 (Red) + B03 (Green)
- Red-edge metric: derived from the red-edge bands (B05/B8A as required by the chosen index implementation)

---

## 6. ML Model Registry

| Stage | Model | Version | Purpose | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1** | `AnomalyDetector` (IsolationForest / Z-score on NDVI) | `anomaly-v0.1.0` | Temporal green-up departure detection | Planned |
| **Stage 2** | `FocalClassifier` (RandomForest / XGBoost) | `rf-v0.1.0` | Species-level spectral discrimination | Planned |
| **Stage 3** | `UNetTexture` (PyTorch U-Net, 512×512 patches) | `unet-v0.1.0` | Spatial texture → hotspot scoring | Planned |
| **Wave 1.5 Benchmark** | `AlphaEarthStage2Benchmark` (RandomForest / XGBoost + annual 64D embeddings) | `alphaearth-benchmark-v0.1.0` | Experimental comparison against the Stage 2 baseline | Proposed |

**Model artifact path:** `./models/{model_name}/{version}/`
**Retraining trigger:** HITL feedback batch ≥ 50 validated/rejected predictions
**Prediction lineage rule:** `invasion_predictions.model_version` stores the Stage 2 classifier version (`rf-v0.1.0` for the current registry). Stage 1 and Stage 3 versions must be captured in logs or sidecar metadata, but not in the `model_version` column.

**Benchmark rule:** AlphaEarth embeddings are permitted only as Wave 1.5 benchmark inputs for Stage 2 comparison work. They MUST NOT replace the Stage 1 NDVI anomaly path, the Planetary Computer scene-ingestion flow, or the production Stage 2 feature vector until benchmark evidence is accepted and both `AGENTS.md` and the constitution are amended again.

---

## 7. The Agent Memory Protocol
**Read-Execute-Write Loop:**
1. **READ**: Read `AGENTS.md` sections 4 (schema), 5 (API contracts), 6 (ML registry) before any feature work.
2. **EXECUTE**: Chain-of-Thought decomposition into atomic tasks. Each task sees only the code it needs (scoped context).
3. **WRITE**: After every architectural decision or pillar completion, update the relevant section of this file.

**Anti-Context Rot rules:**
- Never guess schema column names — check Section 4.
- Never hard-code API URLs — check Section 5.
- Never reference a model by name without checking Section 6 for the correct version string.

---

## 8. Critical Commands (The Justfile Bridge)

| Command | Action | Description |
| :--- | :--- | :--- |
| `just start` | Container Start | Builds if missing; starts Podman compose stack (app + PostGIS) |
| `just run` | Native Start | Runs FastAPI via `uv` for rapid iteration |
| `just db-migrate` | Schema Migration | Applies Alembic migrations against the PostGIS container |
| `just seed-data` | Seed Ground Truth | Fetches iNaturalist + EDDMapS records into `ground_truth_observations` |
| `just research-sync` | Init Notebook | Connects the MCP server to the gaia-atlas notebook (run once after clone) |
| `just research-test` | Test Connection | Verifies MCP connection to gaia-atlas is live |
| `just research-serve` | Start MCP Server | Starts the NotebookLM MCP server for VS Code / Copilot integration |
| `just research-open` | Open in Browser | Opens gaia-atlas in the browser |
| `just verify` | Validate Gate | Runs lint + test together as the required quality gate |
| `just lint` | Clean Code | Ruff check + format |
| `just test` | Run Tests | Pytest via uv |

---

## 9. Active Context & Roadmap

### Completed
- [x] Initialize repository from Genesis template
- [x] Define initial SRS (Software Requirements Specification)
- [x] Author `AGENTS.md` v1.0 with PostGIS schema & API contracts
- [x] Draft `compose.yml` for Podman (PostGIS 16-3.4 + FastAPI app)
- [x] Connect NotebookLM notebook `gaia-atlas` in Section 2
- [x] Specify Wave 0 bootstrap gate in `specs/archive/002-wave0-environment-bootstrap/spec.md`
- [x] Draft Wave 0 implementation plan in `specs/archive/002-wave0-environment-bootstrap/plan.md`
- [x] Add Wave 0 planning artifacts: `research.md`, `data-model.md`, `quickstart.md`
- [x] Generate Wave 0 executable task list in `specs/archive/002-wave0-environment-bootstrap/tasks.md`
- [x] Wave 0 implementation complete — bootstrap runtime, async DB layer, Alembic baseline, `/healthz`, quality gate passed (ruff clean, 8/8 non-integration tests pass)
- [x] Specify Wave 1.5 AlphaEarth benchmark gate in `specs/003-alphaearth-benchmark/spec.md`
- [x] Draft Wave 1.5 implementation plan in `specs/003-alphaearth-benchmark/plan.md`
- [x] Generate Wave 1.5 executable task list in `specs/003-alphaearth-benchmark/tasks.md`
- [x] Specify Wave 1 spatial infrastructure gate in `specs/004-wave1-spatial-infrastructure-seeding/spec.md`
- [x] Draft Wave 1 implementation plan in `specs/004-wave1-spatial-infrastructure-seeding/plan.md`
- [x] Generate Wave 1 executable task list in `specs/004-wave1-spatial-infrastructure-seeding/tasks.md`
- [x] Specify Stage 2 focal classifier gate in `specs/009-stage2-focal-classifier/spec.md`
- [x] Create feature branch `009-stage2-focal-classifier`

### Completed — Pillar I Bootstrap (Wave 0)
- [x] Scaffold FastAPI app structure: `app/api/`, `app/models/`, `app/services/`
- [x] `app/config.py` — pydantic-settings backed runtime config
- [x] `app/db.py` — async SQLAlchemy engine + `get_db` dependency
- [x] `app/main.py` — FastAPI with lifespan, `/healthz`, bootstrap v1 router
- [x] `alembic.ini` + `migrations/env.py` — async Alembic wired to runtime `DATABASE_URL`
- [x] `migrations/versions/0001_baseline.py` — Wave 0 baseline revision (no domain tables)
- [x] Compose dev startup hardened so bind-mounted source no longer masks or overwrites the image-built Linux virtualenv; root endpoint now responds at `/` for local validation

### Completed — Pillar I: Spatial Infrastructure (Wave 1)
- [x] Implement Alembic migration for all four PostGIS tables
- [x] Seed endpoint: `POST /api/v1/observations/sync` (iNaturalist + EDDMapS)
- [x] Implement canonical ORM models for `regions_of_interest`, `invasion_predictions`, `ground_truth_observations`, and `spectral_time_series`
- [x] Implement ROI API endpoints: `POST /api/v1/rois`, `GET /api/v1/rois/{id}`, `GET /api/v1/rois`
- [x] Implement source consumers and seed entrypoint: `app/services/inat_consumer.py`, `app/services/eddmaps_consumer.py`, `app/scripts/seed_observations.py`
- [x] Add Wave 1 API and consumer tests: ROI schema/unit tests, ROI integration tests, observation sync integration tests, retry unit tests
- [x] Complete Phase 6 hardening pass: canonical schema contract integration assertions, retry policy constants with jitter/budget, timeout-safe partial sync handling, sync-run audit logging, deterministic retry test schedules, and `just seed-data-dry-run`
- [x] Research preflight: `just research-sync` + `just research-test` documented; requires manual Google login in NotebookLM browser flow (known limitation, not a blocker)

### Completed — Wave 1.5: AlphaEarth Benchmark Spike
- [x] Author benchmark plan/tasks for `specs/003-alphaearth-benchmark/`
- [x] Implement benchmark scaffolding: `app/services/alphaearth_client.py`, `benchmark_dataset.py`, `alphaearth_benchmark.py`, `benchmark_report.py`, `app/ml/stage2_alphaearth_benchmark.py`, `app/scripts/run_alphaearth_benchmark.py`
- [x] Validate Earth Engine access path — `EE_PROJECT_ID` env var required; clean skip on auth failure
- [x] Compare `rf-v0.1.0` baseline features against `alphaearth-benchmark-v0.1.0` on identical train/test splits
- [x] Record go/no-go recommendation: **no-go** (synthetic cohort: baseline F1=0.4373 vs benchmark F1=0.3750, delta=-0.0623)
- [x] Benchmark report persisted at `docs/research/alphaearth-benchmark-report.md`
- [x] Decision: Do NOT adopt AlphaEarth embeddings for production Stage 2; Planetary Computer baseline remains unchanged

### Completed — Pillar III: AI Execution Chain (spec 007)
- [x] Author `specs/007-wave3-ai-chain/spec.md` — feature specification artifact completed
- [x] Author `specs/007-wave3-ai-chain/plan.md` — full implementation plan (Phase 0 and Phases 3A–3D)
- [x] Author `specs/007-wave3-ai-chain/tasks.md` — executable task list (W3-T001 through W3-T016)
- [x] Tighten `specs/007-wave3-ai-chain/spec.md`, `plan.md`, and `tasks.md` to lock zero-result `message` responses, `validated` filter semantics, deterministic ROI-centroid detection points, 512x512 patch extraction, training-artifact coverage, lineage metadata capture, and research-preflight execution work
- [x] Create feature branch `007-wave3-ai-chain`
- [x] Implement Wave 3 runtime + API + tests (`app/ml/`, `app/services/`, `app/api/v1/`, `app/schemas/`, `app/scripts/`, `tests/`) including deterministic centroid detection, Stage 3 STAC patch extraction, and resilient fallback behavior
- [x] Run full quality gate via `just verify` (ruff clean; pytest 103 passed, 2 skipped)

### Completed — Pillar II: Remote Sensing (spec 005)
- [x] Author `specs/005-pillar2-remote-sensing/spec.md` — feature specification artifact completed
- [x] Author `specs/005-pillar2-remote-sensing/plan.md` — full implementation plan (Phases 0–6)
- [x] Author `specs/005-pillar2-remote-sensing/research.md` — STAC client, index formula, cloud-mask decisions
- [x] Author `specs/005-pillar2-remote-sensing/data-model.md` — schema contract, Pydantic schemas, Stage 1 downstream contract
- [x] Author `specs/005-pillar2-remote-sensing/quickstart.md` — end-to-end validation flow
- [x] Author `specs/005-pillar2-remote-sensing/contracts/scenes-api.md` — POST /ingest + GET /scenes API contract
- [x] Create feature branch `005-pillar2-remote-sensing`
- [x] Migration `0003_spectral_upsert_constraint` — UNIQUE(roi_id, stac_item)
- [x] `app/services/stac_client.py` — Planetary Computer STAC query + URL signing
- [x] `app/services/cloud_mask.py` — QA60 cloud fraction + is_masked flag
- [x] `app/services/indices.py` — NDVI / ENDVI / Red-Edge CIre computation
- [x] `app/services/scene_ingestion.py` — pipeline orchestrator + upsert
- [x] `app/schemas/spectral.py` — SceneIngestRequest/Response, SpectralRecord
- [x] `app/api/v1/scenes.py` — POST /api/v1/scenes/ingest, GET /api/v1/scenes
- [x] Unit tests: test_indices.py, test_cloud_mask.py
- [x] Integration test: test_scene_ingestion.py
- [x] `just verify` gate — 0 lint errors, 0 test failures

### Backlog — Pillar II: Remote Sensing
- [x] Plan authored — see `specs/005-pillar2-remote-sensing/` for full design artifacts
- [ ] Stage 2: Focal classifier training + feature extraction
- [ ] Stage 3: U-Net inference service

### Completed — Stage 2 Focal Classifier Spec (spec 009)
    - [x] Author `specs/009-stage2-focal-classifier/spec.md` — feature specification artifact completed
    - [x] Create `specs/009-stage2-focal-classifier/checklists/requirements.md` — specification quality checklist pass completed
    - [x] Complete spec package readiness cleanup: normalize CLI flag naming (`--roi-ids`), align artifact naming (`classifier.pkl`), remove template placeholders, and reset pre-implementation readiness checkboxes
    - [x] Implement Stage 2 Focal Classifier — Phases 1–3 (T001–T019 + T035/T036/T041): `models/FocalClassifier/rf-v0.1.0/` dir, FeatureExtractor + retry_with_backoff, train_classifier (RF + CV + metrics), flatten metadata.json (H1), infer_predictions (production bug fix), run_stage2_inference.py, 22 unit tests + 5 integration tests; pipeline H3 regression guard; SC-001 ≥99% coverage assertion
    - [x] Quality gate (T041): ruff clean, 135 passed / 2 skipped (unit + Stage 2 integration); DB integration tests excluded (require PostGIS container)

### Completed — Pillar IV: HITL Dashboard (Wave 4)
- [x] `PATCH /api/v1/predictions/{id}/validate` endpoint in `app/api/v1/predictions.py` with `ValidationRequest`/`ValidationResponse` schemas
- [x] `check_retrain_trigger()` in `app/services/retrain_trigger.py` with `RETRAIN_THRESHOLD = 50` and `RETRAINING_TRIGGERED` log emission
- [x] Leaflet + HTMX dashboard at `GET /` with `app/templates/base.html`, `dashboard.html`, and `partials/prediction_card.html`
- [x] Unit tests: `tests/unit/test_validate_endpoint.py` (7 tests), `tests/unit/test_retrain_trigger.py` (5 tests)
- [x] `just verify` gate — 0 lint errors, 89 passed, 2 skipped

---
    ⏱️ **State:** Wave 0 + Wave 1 + Wave 1.5 + Pillar II Remote Sensing + Wave 3 AI Execution Chain + Wave 4 HITL Dashboard + Stage 2 Focal Classifier (spec 009 Phases 1–3) complete; quality gate passing (ruff clean, 135 passed/2 skipped); Phases 4–6 US2/US3 tasks in backlog | 🧠 **Memory:** Updated v2.8 | 🛠️ **Platform:** Podman / macOS Universal
