# Implementation Plan: Pillar II — Remote Sensing (STAC Client, Spectral Indices, Cloud Masking)

**Branch**: `005-pillar2-remote-sensing` | **Date**: 2026-03-30 | **Spec**: [spec.md](./spec.md)
**Input**: AGENTS.md Section 9 backlog — Pillar II: Remote Sensing (three items); see [research.md](./research.md) for all key decisions.

**Note**: This plan covers all three Pillar II backlog items from AGENTS.md Section 9:
the Planetary Computer STAC query service (`app/services/stac_client.py`), the
spectral index calculator (`app/services/indices.py`), and the QA60 cloud-masking
pipeline (`app/services/cloud_mask.py`). It wires results into the existing
`spectral_time_series` table (Wave 1 schema; only one additive unique constraint is
added) and stages time-series data for the Stage 1 `AnomalyDetector` (`anomaly-v0.1.0`).
All authentication, API paths, band names, and error-handling constants are taken
verbatim from AGENTS.md and must not be inferred from memory.

---

## Summary

Pillar II implements the remote-sensing data ingestion foundation for the Invasive Trace
pipeline. A `stac_client.py` service queries Microsoft Planetary Computer for Sentinel-2
L2A scenes covering a given ROI bounding box and date range using `pystac-client` with
per-item `planetary_computer.sign_inplace()` URL signing. A `cloud_mask.py` service reads
the QA60 band via rasterio windowed COG access, computes scene-level cloud fraction (bits
10–11), and returns an `is_masked` flag. An `indices.py` service computes spatial-mean
NDVI, ENDVI, and Red-Edge Chlorophyll Index (CIre) from the relevant bands using numpy.
A `scene_ingestion.py` orchestrator ties these services together and persists results into
`spectral_time_series` via a PostgreSQL upsert on a new unique constraint on
`(roi_id, stac_item)`. New API endpoints (`POST /api/v1/scenes/ingest`,
`GET /api/v1/scenes`) expose the pipeline and return structured ingestion summaries. All
error handling follows Constitution Principle V: HTTP 429 → exponential backoff (max 3
retries); missing tiles → log WARN and skip; `cloud_cover > 0.20` → `is_masked=TRUE`
with NULL spectral values.

---

## Technical Context

<!-- Stack is LOCKED — do not change these values without a constitution amendment. -->

**Language/Version**: Python 3.12 (managed by `uv`)
**Primary Dependencies**: FastAPI, SQLAlchemy (async) + GeoAlchemy2, pystac-client,
planetary-computer, rasterio, numpy, httpx, asyncpg, Pydantic, pytest, pytest-asyncio
**Storage**: PostgreSQL 16 + PostGIS 3.4 — operates exclusively against the existing
`spectral_time_series` table; one additive unique constraint migration planned (`0003`)
**Testing**: `pytest` + `pytest-asyncio` via `just test`
**Target Platform**: Podman-containerized Linux (macOS dev via `just run`)
**Project Type**: Geospatial AI web service
**Performance Goals**:
- STAC query completes within 15 s for a 1-year time window (pystac-client pagination)
- Full ingestion batch completes within 60 s for ≤ 100 scenes (windowed COG reads, ROI bbox clipped)
- `GET /api/v1/scenes` returns results within 2 s for an ROI with up to 365 records
**Constraints**:
- COG-native raster reads only; no full-band download to disk
- All geometries SRID 4326; band bounding boxes reprojected from scene CRS at read time
- `spectral_time_series` column names and types must not change (AGENTS.md Section 4)
- Cloud threshold 20% is constitutionally fixed; must not be parameterised or relaxed
- API keys (`PC_SDK_SUBSCRIPTION_KEY`) from environment variables only
**Scale/Scope**: 1–10 ROIs; 6–24 month time windows; up to 100 scenes per ingestion batch

---

## Constitution Check

*GATE: Must pass before implementation begins. Re-check after design finalization.*

Verify ALL of the following before proceeding:

- [x] **Feature Branch Preflight**: Work is executed on `005-pillar2-remote-sensing`, not on `main` or `004-wave1-spatial-infrastructure-seeding`.
- [x] **Anti-Context Rot (II)**: Checked AGENTS.md Sections 4, 5, and 6 in full. Column names (`ndvi`, `endvi`, `red_edge`, `cloud_cover`, `is_masked`, `stac_item`, `roi_id`, `scene_date`, `platform`) are taken verbatim from Section 4. PC STAC URL (`https://planetarycomputer.microsoft.com/api/stac/v1`) and auth method (`planetary-computer` token signing) are from Section 5. Stage 1 model version `anomaly-v0.1.0` confirmed from Section 6.
- [x] **Tech Stack (III)**: `pystac-client`, `planetary-computer`, `rasterio`, `numpy`, SQLAlchemy async, FastAPI, GeoAlchemy2, Ruff, pytest — all mandated. No `stackstac`, `xarray`, `TensorFlow`, `odc-stac`, or Docker introduced.
- [x] **Spatial Integrity (IV)**: No canonical column changes. Migration `0003` is solely an additive unique constraint on `spectral_time_series (roi_id, stac_item)`. SRID 4326 preserved. `confidence` CHECK constraint in `invasion_predictions` is not touched.
- [x] **API Resilience (V)**: STAC client implements exponential backoff (max 3 retries) for HTTP 429, using the same retry constants pattern established in Wave 1 consumers. Missing band assets → WARN + skip. QA60 missing → treat as 100% cloud (safest fallback). `cloud_cover > 0.20` → `is_masked=TRUE`, spectral values NULL.
- [x] **ML Registry (VI)**: No new model versions introduced. `spectral_time_series` is the training data source for `anomaly-v0.1.0` — this plan does not train, reference, or create any model artifacts. Model registry in AGENTS.md Section 6 remains unchanged.
- [x] **Research-First (I)**: Dev notebook grounding (`just research-sync` + `just research-test`) must be executed before spectral analysis implementation begins. Band contract, index formulas, and cloud-masking decisions are documented in `research.md`.
- [x] **Benchmark Gate (VII)**: AlphaEarth embeddings are NOT used. Planetary Computer is the sole production remote sensing source. The Wave 1.5 benchmark spike remains a separate, isolated track.

*Conclusion: GATE READY FOR IMPLEMENTATION. All seven constitution principles are satisfied on branch `005-pillar2-remote-sensing`.*

---

## Project Structure

### Documentation (this feature)

```text
specs/005-pillar2-remote-sensing/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: STAC client, index formulas, cloud-mask decisions
├── data-model.md        # Phase 1: spectral_time_series schema, Pydantic schemas, data flow
├── quickstart.md        # Phase 1: end-to-end validation steps
├── contracts/
│   └── scenes-api.md    # Phase 1: API contract for /api/v1/scenes
└── tasks.md             # Phase 2 output (/speckit.tasks command — generated)
```

### Source Code (repository root)

```text
app/
├── api/v1/
│   ├── __init__.py                 # Existing — register scenes router here
│   ├── rois.py                     # Existing — unchanged
│   ├── observations.py             # Existing — unchanged
│   └── scenes.py                   # NEW — POST /ingest + GET / router
├── models/
│   └── spectral.py                 # Existing — SpectralTimeSeries ORM (no changes)
├── schemas/
│   ├── roi.py                      # Existing — unchanged
│   └── spectral.py                 # NEW — SceneIngestRequest/Response, SpectralRecord
└── services/
    ├── inat_consumer.py            # Existing — unchanged
    ├── eddmaps_consumer.py         # Existing — unchanged
    ├── stac_client.py              # NEW — Planetary Computer STAC query + signing
    ├── indices.py                  # NEW — NDVI / ENDVI / Red-Edge computation
    ├── cloud_mask.py               # NEW — QA60 cloud fraction + is_masked flag
    └── scene_ingestion.py          # NEW — pipeline orchestrator (STAC → cloud → indices → DB)

tests/
├── unit/
│   ├── test_indices.py             # NEW — unit tests for spectral formula functions
│   └── test_cloud_mask.py          # NEW — unit tests for QA60 masking logic
└── integration/
    └── test_scene_ingestion.py     # NEW — integration tests (mocked STAC + rasterio)

migrations/
└── versions/
    └── 0003_spectral_upsert_constraint.py  # NEW — UNIQUE(roi_id, stac_item)
```

**Structure Decision**: Pillar II extends `app/services/` with three focused service
files plus one orchestrator, adds one Pydantic schema file, one API router, one additive
migration, and three test files. The only modifications to existing files are:
(a) `app/api/v1/__init__.py` — register the `scenes` router, and (b) `app/main.py`
stays unchanged because router registration is delegated to `v1/__init__.py`.
No existing API endpoints, ORM models, or migration files are modified.

---

## Implementation Phases

### Phase 0 — Alembic Migration: Additive Upsert Constraint

**Goal**: Apply migration `0003` before any ingestion code runs, ensuring the upsert
path has a valid unique constraint target in the database.

**Tasks**:
- Create `migrations/versions/0003_spectral_upsert_constraint.py` as an Alembic
  migration that adds `CONSTRAINT uq_spectral_roi_item UNIQUE (roi_id, stac_item)` to
  `spectral_time_series`. No columns are added, renamed, or dropped.
- Set `down_revision = "0002_wave1..."` (chain onto the Wave 1 migration).
- If the development database has been seeded with duplicate `(roi_id, stac_item)` rows
  from manual testing, run a dedup query before `just db-migrate`.
- Verify with `just db-migrate` — migration must apply cleanly.
- Confirm with `just verify` — no lint or test regressions.

### Phase 1 — STAC Client (Planetary Computer Scene Discovery)

**Goal**: Implement `app/services/stac_client.py` — an async-compatible service that
queries the Planetary Computer STAC API and returns a list of signed `pystac.Item`
objects ready for band access.

**Service contract**:

```python
async def query_scenes(
    roi_geom_wkt: str,
    start_date: date,
    end_date: date,
    platform: str = "sentinel-2",
    collection: str = "sentinel-2-l2a",
) -> list[pystac.Item]:
    ...
```

**Tasks**:
- Open `Client.open(PC_STAC_URL)` using the URL from AGENTS.md Section 5:
  `https://planetarycomputer.microsoft.com/api/stac/v1`
- Derive the WGS84 bounding box from `roi_geom_wkt` using `shapely.wkt.loads()`.
  STAC `bbox` parameter expects `[west, south, east, north]`.
- Build an `ItemSearch` with `collections=[collection]`, `bbox=bbox`,
  `datetime=f"{start_date}/{end_date}"`, and optionally
  `query={"eo:cloud_cover": {"lt": 80}}` as a coarse pre-filter.
- Iterate the result pages; apply `planetary_computer.sign_inplace(item)` to each item
  before appending to the return list.
- Wrap the search call in a retry block matching the Wave 1 constants pattern:
  `MAX_RETRIES = 3`, `RETRY_BASE_DELAY_SECONDS = 0.25`,
  `RETRY_EXPONENTIAL_FACTOR = 2.0`, plus proportional jitter.
- On retry exhaustion before any usable scenes are produced, raise a typed
  `StacQueryUnavailableError` that the router maps to HTTP 500.
- For partial scene-level failures after discovery, continue processing and report
  skips in response counters (HTTP 200 path).
- Module-level constants: `PC_STAC_URL`, `SENTINEL2_COLLECTION`, `REQUEST_TIMEOUT_SECONDS`,
  `MAX_RETRIES`, `RETRY_BASE_DELAY_SECONDS`, `RETRY_EXPONENTIAL_FACTOR`.

### Phase 2 — QA60 Cloud Masking

**Goal**: Implement `app/services/cloud_mask.py` — pure functions that read the QA60
band over an ROI bounding box window and return cloud fraction + `is_masked` flag.

**Service contract**:

```python
def compute_cloud_fraction(
    qa60_href: str,
    roi_bounds_4326: tuple[float, float, float, float],
) -> tuple[float, bool]:
    """Returns (cloud_fraction, is_masked) where is_masked = cloud_fraction > 0.20."""
    ...
```

**Tasks**:
- Open `rasterio.open(qa60_href)` inside a
  `rasterio.env.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")`
  context to prevent unnecessary sidecar file probing on COG reads.
- Reproject the WGS84 ROI bounding box to the scene CRS using
  `rasterio.warp.transform_bounds(CRS.from_epsg(4326), src.crs, *roi_bounds_4326)`.
- Build `rasterio.windows.from_bounds(*scene_bounds, transform=src.transform)` and
  read the QA60 band as a uint16 array.
- Apply cloud mask: `cloud_pixels = ((qa60_array >> 10) & 0b11) > 0`.
- `cloud_fraction = cloud_pixels.sum() / cloud_pixels.size`.
- `is_masked = cloud_fraction > 0.20`.
- If the QA60 href is absent from the STAC item: log WARN and return `(1.0, True)`
  as the safest possible fallback.
- Pure function — no DB access, no async, fully unit-testable with synthetic uint16 arrays.

**Band contract compliance**: QA60 bits 10 (opaque cloud) and 11 (cirrus) per
AGENTS.md Section 5 and Constitution Principle V Rule 4.

### Phase 3 — Spectral Index Computation

**Goal**: Implement `app/services/indices.py` — pure functions that accept a signed
band asset href and ROI bounds, perform a windowed COG read, and return the spatial mean
as a float scalar.

**Band contract** (verbatim from AGENTS.md Sections 4 and 5):

| Index | Formula | Bands |
| :--- | :--- | :--- |
| NDVI | `(B08 − B04) / (B08 + B04 + ε)` | B08 (NIR, 842 nm), B04 (Red, 665 nm) |
| ENDVI | `(B08 + B03 − 2·B04) / (B08 + B03 + 2·B04 + ε)` | B08, B03 (Green, 560 nm), B04 |
| Red-Edge CIre | `(B8A / B05) − 1` | B8A (Narrow NIR, 865 nm), B05 (Red Edge, 705 nm) |

where ε = 1e-10. Spatial aggregation: `numpy.nanmean()` over all finite pixels
within the ROI window. Output clamps: NDVI/ENDVI → [−1, 1]; CIre → [−1, 20].

**Service contract**:

```python
def read_band_window(href: str, roi_bounds_4326: tuple) -> np.ndarray | None:
    """Windowed COG read → float32 array; returns None on read failure."""
    ...

def compute_ndvi(b08: np.ndarray, b04: np.ndarray) -> float | None: ...
def compute_endvi(b08: np.ndarray, b03: np.ndarray, b04: np.ndarray) -> float | None: ...
def compute_red_edge(b8a: np.ndarray, b05: np.ndarray) -> float | None: ...
```

**Tasks**:
- Implement `read_band_window()` using the same rasterio COG context pattern as
  `cloud_mask.py`. Reproject ROI bounds to scene CRS before the windowed read.
  Return `None` on `rasterio.errors.RasterioIOError` or empty window.
- Implement the three index functions. They are pure numpy operations and do not
  open files directly — `read_band_window()` is called by the orchestrator.
- Log WARN and return `None` for any entirely-nodata array (no pixels with valid readings
  within the ROI window). This is distinct from a cloud-masked scene — a valid,
  cloud-free scene may still yield a null index if the band geometry clips the ROI.
- Unit tests use synthetic numpy arrays; no rasterio or network calls are needed.

### Phase 4 — Pipeline Orchestrator and Persistence

**Goal**: Implement `app/services/scene_ingestion.py` — the top-level orchestrator that
chains Phases 1–3 and persists results to `spectral_time_series` via async SQLAlchemy upsert.

**Service contract**:

```python
async def run_ingestion(
    roi_id: uuid.UUID,
    start_date: date,
    end_date: date,
    platform: str,
    session: AsyncSession,
) -> SceneIngestResponse:
    ...
```

**Tasks**:
- Fetch the ROI geometry from `regions_of_interest` using `roi_id`; derive WGS84
  bounding box via `geoalchemy2.shape.to_shape(roi.geom).bounds`.
- If ROI not found, raise `HTTPException(status_code=404, ...)` — let the router
  handle the response.
- Query scenes via `stac_client.query_scenes(roi_wkt, start_date, end_date)`.
- For each item:
    1. Extract required spectral asset hrefs: `B03`, `B04`, `B05`, `B08`, `B8A` from
      `item.assets[band_key].href`. Log WARN and skip (`scenes_skipped += 1`) if any
      required spectral asset is absent. Treat `QA60` as optional; if absent,
      `cloud_mask.compute_cloud_fraction()` returns `(1.0, True)`.
  2. Compute `cloud_fraction, is_masked` via `cloud_mask.compute_cloud_fraction()`.
  3. If `is_masked`: set `ndvi=endvi=red_edge=None`.
  4. If not masked: call `read_band_window()` for each required band; compute all
     three indices.
  5. Build a dict matching `SpectralTimeSeries` columns; execute PostgreSQL upsert:
     ```python
     stmt = insert(SpectralTimeSeries).values(**row_data)
     stmt = stmt.on_conflict_do_update(
         constraint="uq_spectral_roi_item",
         set_={col: stmt.excluded[col] for col in update_cols},
     )
     await session.execute(stmt)
     ```
  6. Catch all per-scene exceptions; log at WARN level including the `stac_item` ID;
     increment `scenes_skipped`. Never re-raise.
- Commit once per batch (after all items are processed).
- Return `SceneIngestResponse` with accurate count fields.

### Phase 5 — API Router and Schema

**Goal**: Expose the pipeline via `POST /api/v1/scenes/ingest` and `GET /api/v1/scenes`.

**Tasks**:

- Implement `app/schemas/spectral.py`:
  - `SceneIngestRequest` (Pydantic model with `roi_id`, `start_date`, `end_date`,
    `platform`, and a validator ensuring `end_date >= start_date`)
  - `SceneIngestResponse` (counts + `date_range`)
  - `SpectralRecord` (ORM → response serialisation)

- Implement `app/api/v1/scenes.py`:
  - `POST /ingest` → call `scene_ingestion.run_ingestion()`; return `SceneIngestResponse`
  - `GET /` → query `spectral_time_series` filtered by optional `roi_id`, `start_date`,
    `end_date`, `include_masked`; return `list[SpectralRecord]` ordered by `scene_date ASC`

- Register the router in `app/api/v1/__init__.py`:
  ```python
  from app.api.v1.scenes import router as scenes_router
  router.include_router(scenes_router, prefix="/scenes", tags=["scenes"])
  ```

- No changes to `app/main.py` are required.

### Phase 6 — Tests

**Goal**: Ensure `just verify` passes and all new services are covered.

**Unit tests** (`tests/unit/test_indices.py`):
- `test_ndvi_formula`: synthetic 2×2 float32 arrays for B08/B04; verify formula output.
- `test_endvi_formula`: same pattern for three-band formula.
- `test_red_edge_formula`: verify CIre output for B8A/B05.
- `test_zero_denominator_guard`: arrays where B08+B04=0 → returns finite value (not inf/nan).
- `test_all_nodata_returns_none`: fully nodata array (all np.nan) → `None` return.

**Unit tests** (`tests/unit/test_cloud_mask.py`):
- `test_clear_scene`: QA60 array with all zero bits → `cloud_fraction=0.0`, `is_masked=False`.
- `test_fully_clouded`: all pixels with bit 10 set → `cloud_fraction=1.0`, `is_masked=True`.
- `test_threshold_boundary_below`: `cloud_fraction=0.20` exactly → `is_masked=False`.
- `test_threshold_boundary_above`: `cloud_fraction=0.201` → `is_masked=True`.
- `test_cirrus_bit`: QA60 with bit 11 set → counted as cloud.
- `test_missing_qa60_href`: function called with `href=None` → `(1.0, True)`.

**Integration tests** (`tests/integration/test_scene_ingestion.py`):
- Patch `stac_client.query_scenes` to return a list of mock `pystac.Item` objects with
  synthetic asset hrefs.
- Patch `rasterio.open` to return mock datasets yielding synthetic band arrays.
- `test_clean_scene_persisted`: cloud_fraction=0.05 → row with valid index values written.
- `test_masked_scene_persisted`: cloud_fraction=0.35 → row with `is_masked=True`, NULL indices.
- `test_upsert_idempotency`: run ingestion twice for the same item → second run produces
  `scenes_inserted=0, scenes_updated=1`.
- `test_missing_asset_skipped`: item with missing B08 href → `scenes_skipped=1`, no row written.
- `test_roi_not_found_raises_404`: unknown `roi_id` → `HTTPException(404)`.

---

## Risk Management

| Risk | Mitigation |
| :--- | :--- |
| PC auth token expiry mid-batch | `pc.sign_inplace()` refreshes per-item; no long-lived token state cached in the client |
| ROI bounding box straddles two UTM zones | Use `rasterio.warp.transform_bounds()` per-scene using the scene's native CRS; never assume a fixed UTM zone |
| Large ROI bbox causes excessive COG egress | Windowed reads are clipped to the ROI bbox; `GDAL_HTTP_TIMEOUT` env var must be set to bound hanging reads |
| QA60 asset absent from a STAC item | Log WARN; treat as 100% cloud (safe default); set `is_masked=TRUE`; do not skip the row entirely |
| Band asset absent for an otherwise valid scene | Log WARN with `stac_item` ID; skip entire scene; increment `scenes_skipped` |
| `0003` migration constraint conflicts with existing duplicate rows | Pre-apply dedup check; document in quickstart.md |
| NDVI time series has gaps from cloud-masked scenes | Stage 1 anomaly detector must filter `is_masked=FALSE` when building training sequences (documented in data-model.md downstream contract) |
| Concurrent ingestion calls for the same ROI + date range | Upsert on `(roi_id, stac_item)` is idempotent; concurrent calls resolve via DB constraint, not application logic |
| Wave 1.5 AlphaEarth benchmark work diverging from this STAC baseline | AlphaEarth benchmark gate (Constitution VII) prevents any production pipeline displacement; pipelines are strictly isolated |

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :-------- | :--------- | :---------------------------------- |
| None | N/A | N/A |
