# API Contract: Scenes Endpoints (Spectral Time Series Ingestion)

**Base path**: `/api/v1/scenes`
**Router file**: `app/api/v1/scenes.py`
**All endpoints require a running PostGIS container and a seeded `regions_of_interest` row.**

---

## POST /api/v1/scenes/ingest

Triggers Planetary Computer STAC scene discovery, QA60 cloud masking, spectral index
computation (NDVI, ENDVI, Red-Edge), and upsert into `spectral_time_series` for the
specified ROI and date window.

### Request Body (application/json)

```json
{
  "roi_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "start_date": "2024-04-01",
  "end_date": "2024-09-30",
  "platform": "sentinel-2"
}
```

| Field | Type | Required | Default | Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `roi_id` | UUID | Yes | — | Must reference an existing row in `regions_of_interest` |
| `start_date` | string (date) | Yes | — | ISO 8601 format |
| `end_date` | string (date) | Yes | — | ISO 8601; `end_date >= start_date` |
| `platform` | string | No | `"sentinel-2"` | Wave 005 supports only `sentinel-2`; other values return 422 |

### Responses

#### 200 OK — Ingestion complete (fully or partially successful)

```json
{
  "roi_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "scenes_queried": 12,
  "scenes_inserted": 8,
  "scenes_updated": 1,
  "scenes_masked": 2,
  "scenes_skipped": 1,
  "date_range": {
    "start": "2024-04-01",
    "end": "2024-09-30"
  }
}
```

| Field | Type | Notes |
| :--- | :--- | :--- |
| `roi_id` | UUID | Echo of the request ROI |
| `scenes_queried` | int | Total STAC items returned from Planetary Computer |
| `scenes_inserted` | int | New rows written to `spectral_time_series` |
| `scenes_updated` | int | Existing rows overwritten via upsert on `(roi_id, stac_item)` |
| `scenes_masked` | int | Rows with `is_masked=TRUE` (cloud_cover > 0.20) |
| `scenes_skipped` | int | Items skipped: missing band assets, read errors, or unrecoverable failures |
| `date_range` | object | `{"start": date, "end": date}` echoing the requested window |

#### 404 Not Found — ROI does not exist

```json
{"detail": "ROI 3fa85f64-5717-4562-b3fc-2c963f66afa6 not found"}
```

#### 422 Unprocessable Entity — Validation failure

Returned by FastAPI for invalid UUID, `end_date < start_date`, or unsupported `platform` value.

```json
{
  "detail": [
    {
      "loc": ["body", "end_date"],
      "msg": "end_date must be >= start_date",
      "type": "value_error"
    }
  ]
}
```

#### 500 Internal Server Error — Unrecoverable STAC query failure

Returned only when all retries are exhausted and zero scenes can be returned (e.g.,
Planetary Computer is completely unreachable). Partial failures are reported in the
200 response via `scenes_skipped`.

---

## GET /api/v1/scenes

Lists persisted spectral time-series records from `spectral_time_series`, optionally
filtered by ROI, date range, and cloud-mask status.

### Query Parameters

| Parameter | Type | Required | Default | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `roi_id` | UUID | No | — | Filter by `roi_id` |
| `start_date` | string (date) | No | — | ISO 8601; inclusive lower bound on `scene_date` |
| `end_date` | string (date) | No | — | ISO 8601; inclusive upper bound on `scene_date` |
| `include_masked` | bool | No | `false` | If `true`, include rows where `is_masked=TRUE` |

### Example Request

```
GET /api/v1/scenes?roi_id=3fa85f64-5717-4562-b3fc-2c963f66afa6&start_date=2024-04-01&include_masked=false
```

### Responses

#### 200 OK

```json
[
  {
    "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "roi_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "scene_date": "2024-05-12",
    "platform": "sentinel-2",
    "stac_item": "S2B_MSIL2A_20240512T175909_R141_T13TGF_20240512T212359",
    "ndvi": 0.612,
    "endvi": 0.481,
    "red_edge": 1.243,
    "cloud_cover": 0.04,
    "is_masked": false
  },
  {
    "id": "c0a47b62-66be-4d4b-948e-7fef459f8bac",
    "roi_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "scene_date": "2024-06-07",
    "platform": "sentinel-2",
    "stac_item": "S2A_MSIL2A_20240607T175911_R141_T13TGF_20240607T212407",
    "ndvi": null,
    "endvi": null,
    "red_edge": null,
    "cloud_cover": 0.38,
    "is_masked": true
  }
]
```

Results are ordered by `scene_date ASC`. An empty array is returned when no matching
records exist (not a 404).

#### 422 Unprocessable Entity — Invalid query parameters

---

## Error Handling Contract

Per Constitution Principle V, all STAC and rasterio calls MUST implement:

| Failure Mode | Behaviour |
| :--- | :--- |
| HTTP 429 (rate limit) | Exponential backoff, max 3 retries. If at least one usable scene is processed, return 200 with `scenes_skipped` incremented for failed scenes; if retries are exhausted and zero usable scenes remain, return 500 |
| Missing band asset (e.g., B08 href absent) | Log WARN with `stac_item` ID; skip scene; increment `scenes_skipped` |
| Rasterio read error / timeout | Log WARN; skip scene; increment `scenes_skipped` |
| QA60 band missing | Treat as 100% cloud covered (safe fallback); set `is_masked=TRUE` |
| `cloud_cover > 0.20` | Persist with `is_masked=TRUE`, `ndvi=endvi=red_edge=NULL` |
| ROI not found in DB | Return 404 immediately; do not initiate STAC query |
| All retries exhausted, zero scenes returned | Return 500 with detail message |

No unhandled Python exception from external API or rasterio calls may propagate into
the FastAPI request lifecycle.
