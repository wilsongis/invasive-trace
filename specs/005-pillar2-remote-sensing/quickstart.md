# Quickstart: Pillar II — Remote Sensing

## Prerequisites

- Wave 0 + Wave 1 complete: PostGIS container healthy, canonical four-table schema applied
- `PC_SDK_SUBSCRIPTION_KEY` set in `.env` (optional for public Planetary Computer access;
  required for higher rate-limit tier)
- `just start` running (app + PostGIS containers healthy)
- At least one ROI exists; create one via `POST /api/v1/rois` if needed

---

## Validation Flow

### 1. Apply the additive Pillar II migration

```bash
just db-migrate
```

Expected result:

- Alembic applies `0003_spectral_upsert_constraint`
- Unique constraint `uq_spectral_roi_item` added to `spectral_time_series (roi_id, stac_item)`
- No data is altered; migration completes without error

### 2. Run the quality gate

```bash
just verify
```

Expected result:

- 0 Ruff lint errors
- 0 test failures (unit tests for `test_indices.py` and `test_cloud_mask.py` pass
  without network access; integration tests use mocked STAC + rasterio calls)

If `just verify` fails, isolate with:

```bash
just lint
just test
```

### 3. Create a test ROI (skip if one already exists)

```bash
curl -s -X POST http://localhost:8000/api/v1/rois \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pillar II Test ROI",
    "description": "Small Southern Grassland study area for Pillar II validation",
    "wkt": "POLYGON((-104.5 40.0, -104.4 40.0, -104.4 40.1, -104.5 40.1, -104.5 40.0))"
  }' | python3 -m json.tool
```

Copy the returned `id` for use in the next steps.

### 4. Trigger spectral scene ingestion

```bash
curl -s -X POST http://localhost:8000/api/v1/scenes/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "roi_id": "<YOUR_ROI_UUID>",
    "start_date": "2024-04-01",
    "end_date": "2024-06-30"
  }' | python3 -m json.tool
```

Expected result: A summary payload similar to:

```json
{
  "roi_id": "<YOUR_ROI_UUID>",
  "scenes_queried": 6,
  "scenes_inserted": 5,
  "scenes_updated": 0,
  "scenes_masked": 1,
  "scenes_skipped": 0,
  "date_range": { "start": "2024-04-01", "end": "2024-06-30" }
}
```

### 5. List persisted spectral records

```bash
curl -s "http://localhost:8000/api/v1/scenes?roi_id=<YOUR_ROI_UUID>" | python3 -m json.tool
```

Expected result: Array of `SpectralRecord` objects ordered by `scene_date ASC`, with
`ndvi`, `endvi`, and `red_edge` populated for unmasked scenes.

### 6. Verify cloud-masked scenes are correctly flagged

Inspect rows where `is_masked=TRUE`:

```bash
curl -s "http://localhost:8000/api/v1/scenes?roi_id=<YOUR_ROI_UUID>&include_masked=true" \
  | python3 -c "import sys, json; [print(r) for r in json.load(sys.stdin) if r['is_masked']]"
```

Expected result: Cloud-masked rows show `cloud_cover > 0.20` and `ndvi = null`.

### 7. Verify upsert idempotency

Re-run step 4 with the same date range. Expected result:

```json
{
  "scenes_inserted": 0,
  "scenes_updated": 5,
  ...
}
```

No duplicate rows in `spectral_time_series`.

### 8. Run latency smoke checks

```bash
uv run pytest tests/integration/test_scene_ingestion.py -k latency
```

Expected result:

- STAC discovery smoke check <= 15 seconds
- Ingestion smoke check <= 60 seconds
- Scene listing smoke check <= 2 seconds

---

## Completion Standard

Pillar II is complete only when:

- `0003_spectral_upsert_constraint` migration applies without error
- `just verify` passes (all unit + integration tests, 0 lint errors)
- At least one ROI can be successfully ingested from Planetary Computer
- QA60 masking behavior is verified deterministically: threshold boundary unit tests pass and any masked rows observed in integration output satisfy `cloud_cover > 0.20` with NULL index values
- `GET /api/v1/scenes` returns temporally ordered records for the ROI with correct index values
- Upsert idempotency confirmed (re-ingest of same range produces `scenes_inserted=0`)
- AGENTS.md Section 9 roadmap updated to mark all three Pillar II backlog items complete
