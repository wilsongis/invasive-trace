# Data Model: Pillar II — Remote Sensing

Pillar II does not introduce new canonical domain tables. It operates against the
existing contract-locked `spectral_time_series` table (created and applied in
Wave 1 migration `0002_wave1_canonical_spatial_tables`) and adds one additive
unique constraint via migration `0003`.

---

## Existing Target Table: spectral_time_series

Contract-locked per AGENTS.md Section 4. Column names and types MUST NOT change.

| Column | Type | Nullable | Notes |
| :--- | :--- | :--- | :--- |
| `id` | UUID (PK) | No | `gen_random_uuid()` default |
| `roi_id` | UUID (FK → `regions_of_interest`) | Yes | ON DELETE CASCADE |
| `scene_date` | DATE | No | Sentinel-2 acquisition date |
| `platform` | TEXT | No | CHECK IN ('sentinel-2', 'landsat-hls', 'naip') |
| `stac_item` | TEXT | No | STAC item ID from Planetary Computer |
| `ndvi` | FLOAT | Yes | NULL when `is_masked=TRUE` |
| `endvi` | FLOAT | Yes | NULL when `is_masked=TRUE` |
| `red_edge` | FLOAT | Yes | Red-Edge CIre; NULL when `is_masked=TRUE` |
| `cloud_cover` | FLOAT | Yes | Scene-level cloud fraction (QA60); always written |
| `is_masked` | BOOLEAN | Yes | DEFAULT FALSE; application always writes TRUE/FALSE based on cloud threshold |

Existing ORM model: `app/models/spectral.py` — `SpectralTimeSeries`. No changes required.

---

## Additive Migration: 0003_spectral_upsert_constraint

A unique constraint is added on `(roi_id, stac_item)` to enable idempotent upsert
on pipeline reruns. No existing columns are altered.

```sql
ALTER TABLE spectral_time_series
    ADD CONSTRAINT uq_spectral_roi_item UNIQUE (roi_id, stac_item);
```

Migration file path: `migrations/versions/0003_spectral_upsert_constraint.py`

**Pre-apply check**: If the application has been seeded with duplicate `(roi_id, stac_item)`
pairs from development runs, those must be deduplicated before this migration is applied.

---

## New Pydantic Schemas (app/schemas/spectral.py)

### SceneIngestRequest

| Field | Type | Required | Validation |
| :--- | :--- | :--- | :--- |
| `roi_id` | UUID | Yes | Must reference an existing ROI |
| `start_date` | date | Yes | ISO 8601 |
| `end_date` | date | Yes | ISO 8601; `end_date >= start_date` |
| `platform` | str | No | DEFAULT `"sentinel-2"`; Wave 005 accepts only `sentinel-2` and rejects others with 422 |

### SceneIngestResponse

| Field | Type | Notes |
| :--- | :--- | :--- |
| `roi_id` | UUID | Echo of the request ROI |
| `scenes_queried` | int | Total STAC items returned by the PC query |
| `scenes_inserted` | int | New rows written to `spectral_time_series` |
| `scenes_updated` | int | Existing rows overwritten on conflict (upsert hit) |
| `scenes_masked` | int | Rows inserted/updated with `is_masked=TRUE` |
| `scenes_skipped` | int | Items skipped due to missing band assets or unrecoverable errors |
| `date_range` | dict | `{"start": date, "end": date}` echoing the request window |

### SpectralRecord

| Field | Type | Notes |
| :--- | :--- | :--- |
| `id` | UUID | |
| `roi_id` | UUID | |
| `scene_date` | date | |
| `platform` | str | |
| `stac_item` | str | |
| `ndvi` | float \| None | |
| `endvi` | float \| None | |
| `red_edge` | float \| None | |
| `cloud_cover` | float \| None | |
| `is_masked` | bool | |

---

## Computed Values (not persisted separately)

These intermediate values are computed inside `app/services/indices.py` and
`app/services/cloud_mask.py` and written into `spectral_time_series` as scalars.
They are never stored in separate tables.

| Value | Formula | Input Bands |
| :--- | :--- | :--- |
| NDVI | `(B08 − B04) / (B08 + B04 + ε)` | B08 (NIR), B04 (Red) |
| ENDVI | `(B08 + B03 − 2·B04) / (B08 + B03 + 2·B04 + ε)` | B08, B03, B04 |
| Red-Edge CIre | `(B8A / B05) − 1` | B8A (Narrow NIR), B05 (Red Edge) |
| Cloud Fraction | QA60 bits 10–11 contaminated / total pixels | QA60 |

where ε = 1e-10 (zero-denominator guard). Spatial aggregation: `numpy.nanmean()`
over all unmasked pixels within the ROI window.

---

## Data Flow

```text
regions_of_interest.geom (POLYGON, 4326)
        │
        ▼
  stac_client.py ──► Planetary Computer STAC API
        │                 (sentinel-2-l2a, date range, bbox filter)
        ▼
      List[pystac.Item]  (required spectral assets: B03, B04, B05, B08, B8A; optional QA60 with masked fallback)
        │
        ├──► cloud_mask.py (QA60 windowed read → cloud_fraction, is_masked)
        │
        ├──► indices.py    (B08/B04/B03/B05/B8A windowed reads → ndvi, endvi, red_edge)
        │
        ▼
  scene_ingestion.py ──► spectral_time_series (upsert on roi_id, stac_item)
        │
        ▼
  SceneIngestResponse  (scenes_queried, _inserted, _updated, _masked, _skipped)
```

---

## Stage 1 Downstream Contract

The `AnomalyDetector` (`anomaly-v0.1.0`) will query `spectral_time_series` filtered
by `roi_id` and ordered by `scene_date ASC` to build NDVI time series vectors. The
query contract expected by Stage 1 is:

```sql
SELECT scene_date, ndvi
FROM   spectral_time_series
WHERE  roi_id = :roi_id
  AND  is_masked = FALSE
ORDER  BY scene_date ASC;
```

No schema changes are required for Stage 1 access. The Stage 1 training script will
be implemented in a later wave (Pillar III).
