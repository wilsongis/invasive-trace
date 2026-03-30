# Research Notes: Pillar II — Remote Sensing (STAC Client, Spectral Indices, Cloud Masking)

## Objective

Define the technical approach for querying Sentinel-2 L2A scenes from Microsoft
Planetary Computer, computing spectral vegetation indices (NDVI, ENDVI, Red-Edge),
applying QA60 cloud masking, and persisting the resulting time-series records into
`spectral_time_series`. All decisions are grounded in AGENTS.md and the gaia-atlas
notebook research sources.

## Confirmed Inputs from AGENTS.md

- Planetary Computer STAC endpoint: `https://planetarycomputer.microsoft.com/api/stac/v1`
- Auth: Token via `planetary-computer` library (`pc.sign_inplace(item)`)
- Sentinel-2 collection ID: `sentinel-2-l2a`
- Band contract (AGENTS.md Section 5):
  - NDVI: B08 (NIR, 842 nm) + B04 (Red, 665 nm)
  - ENDVI: B08 (NIR) + B04 (Red) + B03 (Green, 560 nm)
  - Red-edge metric (CIre): B8A (Narrow NIR, 865 nm) / B05 (Red Edge, 705 nm) - 1
  - Cloud masking: QA60 band — bit 10 = opaque cloud, bit 11 = cirrus
- `spectral_time_series` schema is contract-locked per AGENTS.md Section 4
- Stage 1 anomaly detector (`AnomalyDetector`, version `anomaly-v0.1.0`) will consume
  the NDVI column from this table

---

## Decisions

### 1. STAC Client Library

**Decision**: Use `pystac_client.Client.open()` against the Planetary Computer STAC
endpoint, with `planetary_computer.sign_inplace(item)` applied to each returned item
before any asset href is accessed.

**Rationale**: `pystac-client` is the mandated library (AGENTS.md Section 3). The
`planetary-computer` library handles token-based URL signing transparently — each
asset href (e.g., B08, QA60) is signed per-item, and refreshed automatically on
expiry. Direct httpx STAC queries were considered but rejected because pystac-client
handles server-side pagination, item-search filtering, and result de-duplication
natively.

**Alternatives considered**: Direct `httpx` STAC queries — rejected because
pystac-client handles pagination transparently and is already in pyproject.toml.

---

### 2. COG Band Access with rasterio

**Decision**: Use `rasterio.open(signed_href)` inside a
`rasterio.env.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")`
context. Perform windowed reads clipped to the ROI bounding box using
`rasterio.windows.from_bounds()` to minimise per-scene egress.

**Rationale**: COG-native reads are constitutionally mandated (III). Windowed reads
avoid downloading full granules (~100 MB each) for small ROIs. Each Sentinel-2 L2A
band asset URL on Planetary Computer is a Cloud-Optimized GeoTIFF accessible via
GDAL's VSI virtual filesystem with rasterio.

**Alternatives considered**: `stackstac` for lazy xarray-backed COG reads — rejected
because it introduces xarray as a heavy non-mandated dependency. `odc-stac` — rejected
for the same reason.

---

### 3. Spectral Index Formulas

**Decision**:

| Index | Formula | Bands | Clamp |
| :--- | :--- | :--- | :--- |
| NDVI | `(B08 - B04) / (B08 + B04 + ε)` | B08, B04 | [-1, 1] |
| ENDVI | `(B08 + B03 - 2·B04) / (B08 + B03 + 2·B04 + ε)` | B08, B03, B04 | [-1, 1] |
| Red-Edge CIre | `(B8A / B05) - 1` | B8A, B05 | [-1, 20] |

where ε = 1e-10 to guard against zero-denominator. Each function returns the spatial
mean computed via `numpy.nanmean()` over the unmasked ROI window pixels.

**Rationale**: NDVI is the industry-standard phenology index for vegetation monitoring
and the primary input for Stage 1 anomaly detection. ENDVI incorporates green
reflectance to reduce soil background interference in sparse cover types. The Red-Edge
Chlorophyll Index (CIre, Gitelson et al. 2003) uses B8A/B05 as mandated by AGENTS.md
Section 5 ("B05/B8A as required by the chosen index implementation") and is sensitive
to chlorophyll concentration changes characteristic of early invasive species
establishment.

**NDRE alternative considered**: `(B8A - B05) / (B8A + B05 + ε)` — normalised
difference form offering comparable sensitivity. CIre preferred because it produces
absolute chlorophyll-correlated values rather than a normalised ratio, which provides
richer contrast in the Stage 1 anomaly feature space.

---

### 4. Cloud Masking via QA60

**Decision**: Read the QA60 uint16 band over the ROI bounding box window. Apply
`(qa60_array >> 10) & 0b11 > 0` to mark cloud-contaminated pixels (bits 10–11).
Compute cloud fraction as `contaminated_pixels / total_pixels`. If
`cloud_fraction > 0.20`: persist the scene with `is_masked=TRUE` and
`ndvi=endvi=red_edge=NULL`. Otherwise compute all three spectral indices.

**Rationale**: QA60 pixel-level masking is more accurate than STAC-metadata `eo:cloud_cover`
for small ROIs, where a cloud fringe at one tile edge can contaminate a portion of the
study area while leaving the remainder clear. The 20% threshold is constitutionally
fixed (Principle V, Rule 3) and must not be changed without a constitution amendment.

**STAC metadata alternative**: Reading `item.properties["eo:cloud_cover"]` at the
granule level — accepted as a fast pre-filter to skip obviously bad scenes (> 80%)
before making a COG request, but NOT used as the sole masking criterion; QA60
pixel-level check is always the authoritative decision.

---

### 5. Upsert Strategy for spectral_time_series

**Decision**: Use PostgreSQL `INSERT ... ON CONFLICT (roi_id, stac_item) DO UPDATE`
(SQLAlchemy `insert().on_conflict_do_update()`). A unique constraint on
`(roi_id, stac_item)` is added via an additive Alembic migration `0003`.

**Rationale**: An ROI may be re-ingested for the same time window (pipeline reruns,
backfill). The natural idempotency key is `(roi_id, stac_item)` — a given STAC item
is ingested at most once per ROI. Application-level dedup via a SELECT-before-INSERT
is a race condition and performs worse under concurrent ingest calls.

**Schema impact**: One additive unique constraint on existing table — no column name
or geometry type changes; fully compliant with Spatial Integrity principle (IV).

---

### 6. Synchronous vs. Asynchronous Scene Ingestion

**Decision**: `POST /api/v1/scenes/ingest` runs the full pipeline synchronously within
the FastAPI request lifecycle for the current scope (up to ~100 scenes per call).

**Rationale**: The constitution does not mandate a task queue for Pillar II. Scene
counts for the Southern Grassland Institute's current study areas are small enough that
a 30–60 s synchronous request is acceptable for a batch endpoint. A background-task
approach (Celery/ARQ) introduces a broker dependency and is deferred to a later wave
if measured latency becomes problematic.

**FastAPI BackgroundTask alternative**: Would return 202 immediately without ingestion
results — rejected because the `SceneIngestResponse` summary payload (counts of
inserted, masked, skipped) is the primary success signal for the caller.

---

### 7. No New Domain Table Migration Required (Except Additive Constraint)

**Decision**: All four canonical tables exist after Wave 1 migration `0002`. Pillar II
adds only migration `0003`, which appends a unique constraint on
`spectral_time_series (roi_id, stac_item)`. No column names or geometry types change.

**Impact on AGENTS.md**: Section 4 schema contract is not altered; a note about the
upsert constraint is added. No constitution amendment required.

---

## Open Constraints

- Scene ingestion must remain COG-native; full raster patch storage is deferred to Stage 3.
- Each scene is represented by the spatial mean of each index over the ROI window — a
  single representative scalar per (roi, scene, index). Full pixel arrays are not yet persisted.
- `PC_SDK_SUBSCRIPTION_KEY` is optional for public Planetary Computer access but required
  for higher-tier rate limits; read exclusively from the environment variable.
- GDAL timeout must be set via environment variable (`GDAL_HTTP_TIMEOUT`) to prevent
  COG reads from hanging indefinitely.
- Band reprojection: Sentinel-2 bands are natively in UTM. Rasterio reads using a
  WGS84 (SRID 4326) bounding box require reprojection of the window geometry to the
  scene CRS using `rasterio.warp.transform_bounds` before windowed read.
