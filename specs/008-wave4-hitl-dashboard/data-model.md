# Data Model: Wave 4 — Human-in-the-Loop (HITL) Dashboard

Wave 4 does not introduce new canonical domain tables or schema migrations. It operates against
the existing contract-locked `invasion_predictions` table (created and applied in Wave 1 migration
`0002_wave1_canonical_spatial_tables`) and updates two existing columns: `validated` and
`validator_notes`.

---

## Existing Target Table: invasion_predictions

Contract-locked per `AGENTS.md` Section 4. Column names and types MUST NOT change.

| Column | Type | Nullable | Notes |
| :--- | :--- | :--- | :--- |
| `id` | UUID (PK) | No | `gen_random_uuid()` default |
| `roi_id` | UUID (FK → `regions_of_interest`) | No | ON DELETE CASCADE |
| `species_label` | TEXT | No | e.g. "Bromus tectorum" |
| `confidence` | FLOAT | No | CHECK BETWEEN 0.0 AND 1.0 |
| `hotspot_score` | FLOAT | Yes | Stage 3 ecological spread risk (0–1) |
| `geom` | GEOMETRY(POINT, 4326) | No | WGS84 point |
| `model_version` | TEXT | No | Stage 2 classifier version, e.g. "rf-v0.1.0" |
| `predicted_at` | TIMESTAMPTZ | No | DEFAULT now() |
| `validated` | BOOLEAN | **Yes** | **Wave 4 updates this**: `NULL` = pending, `TRUE` = confirmed, `FALSE` = rejected |
| `validator_notes` | TEXT | **Yes** | **Wave 4 updates this**: free-text reviewer comment |

Existing ORM model: `app/models/prediction.py` — `InvasionPrediction`. No changes required —
the model already declares `validated: Mapped[bool | None]` and `validator_notes: Mapped[str | None]`.

---

## New Pydantic Schemas (app/schemas/prediction.py)

These schemas are additive to the existing `PredictionProperties`, `PredictionFeature`, and
`PredictionFeatureCollection` schemas from Wave 3.

### ValidationRequest

Request body for `PATCH /api/v1/predictions/{id}/validate`.

| Field | Type | Required | Validation |
| :--- | :--- | :--- | :--- |
| `validated` | bool | **Yes** | Must be a boolean (`true` or `false`); 422 if missing or non-boolean |
| `validator_notes` | str \| None | No | Max 1000 characters; `NULL` if omitted |

**Example request body (confirm):**
```json
{
  "validated": true,
  "validator_notes": "Confirmed via field survey on 2026-04-01"
}
```

**Example request body (reject):**
```json
{
  "validated": false,
  "validator_notes": "Misclassified — native species"
}
```

### ValidationResponse

Response body for `PATCH /api/v1/predictions/{id}/validate`.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `id` | UUID | Prediction ID |
| `roi_id` | UUID | Region of interest |
| `species_label` | str | Species label |
| `confidence` | float | Confidence score [0.0, 1.0] |
| `hotspot_score` | float \| None | Hotspot risk score |
| `model_version` | str | Stage 2 classifier version |
| `predicted_at` | datetime | Inference timestamp |
| `validated` | bool \| None | Updated validation state |
| `validator_notes` | str \| None | Updated reviewer notes |
| `retraining_triggered` | bool | `True` if reviewed count ≥ 50 |

**Example response body:**
```json
{
  "id": "a1b2c3d4-...",
  "roi_id": "e5f6a7b8-...",
  "species_label": "Bromus tectorum",
  "confidence": 0.87,
  "hotspot_score": 0.72,
  "model_version": "rf-v0.1.0",
  "predicted_at": "2026-04-01T12:00:00Z",
  "validated": true,
  "validator_notes": "Confirmed via field survey",
  "retraining_triggered": false
}
```

---

## Retraining Trigger Query

The `check_retrain_trigger()` function executes the following query:

```sql
SELECT COUNT(*) AS reviewed_count
FROM   invasion_predictions
WHERE  validated IS NOT NULL;
```

If `reviewed_count >= RETRAIN_THRESHOLD` (50), the function logs `RETRAINING_TRIGGERED` at
INFO level and returns `True`; otherwise it returns `False`.

No schema changes are required for this query.

---

## Data Flow

```text
PATCH /api/v1/predictions/{id}/validate
  │
  ├─► ValidationRequest (validated: bool, validator_notes: str|null)
  │
  ├─► Lookup invasion_predictions WHERE id = :id
  │     └─► 404 if not found
  │
  ├─► UPDATE invasion_predictions
  │       SET validated = :validated,
  │           validator_notes = :validator_notes
  │       WHERE id = :id
  │
  ├─► check_retrain_trigger(db)
  │     └─► SELECT COUNT(*) WHERE validated IS NOT NULL
  │           └─► If count >= 50: log RETRAINING_TRIGGERED, return True
  │
  └─► ValidationResponse (updated record + retraining_triggered: bool)

GET / → dashboard.html
  │
  ├─► Leaflet map initialises
  │     └─► GET /api/v1/predictions → L.geoJSON(markers)
  │
  └─► Sidebar renders prediction_card.html partials
        └─► HTMX PATCH → /api/v1/predictions/{id}/validate
              └─► Swap updated card fragment (confirmed/rejected state)
```

---

## HTMX Partial Contract: prediction_card.html

The `prediction_card.html` template renders a single prediction as an HTML fragment suitable
for HTMX `outerHTML` swap. It is used in two contexts:

1. **Initial sidebar render**: Rendered as part of the dashboard page load (server-side).
2. **POST-PATCH swap**: Returned as the response body of the PATCH endpoint when the request
   includes `HX-Request: true` header (HTMX auto-header), or rendered as a separate partial
   endpoint if needed.

**Required visual elements:**
- Species label (text)
- Confidence score (numeric, 0–1)
- Hotspot score (numeric, 0–1 or "N/A")
- Validation state badge: "Pending" (gray), "Confirmed" (green), "Rejected" (red)
- Confirm button (visible when `validated IS NULL` or `validated = FALSE`)
- Reject button (visible when `validated IS NULL` or `validated = TRUE`)
- Validator notes (text, if present)

**HTMX attributes on buttons:**
- `hx-patch="/api/v1/predictions/{id}/validate"`
- `hx-vals='js:{"validated": true, "validator_notes": document.getElementById("notes-{id}").value}'`
- `hx-swap="outerHTML"`
- `hx-target="closest .prediction-card"`
- `hx-on::after-request="if(event.detail.failed) { /* show error indicator */ }"`
