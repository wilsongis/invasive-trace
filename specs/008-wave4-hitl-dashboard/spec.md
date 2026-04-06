# Feature Specification: Wave 4 — Human-in-the-Loop (HITL) Dashboard

**Feature Branch**: `008-wave4-hitl-dashboard`
**Created**: 2026-04-06
**Status**: Ready for Implementation
**Input**: User description: "Wave 4: HITL Dashboard — Leaflet map + HTMX prediction review panel with confirm/reject workflow and retraining trigger"

## Overview

Wave 4 delivers the expert review dashboard that closes the loop between AI-generated invasion predictions and field-validated ground truth. It depends directly on Wave 3 (`invasion_predictions` populated by the three-stage AI pipeline) and produces validated prediction records that will trigger model retraining when the reviewed batch reaches 50 records.

The dashboard consists of three layers:

1. **Validation API** — `PATCH /api/v1/predictions/{id}/validate` transitions `validated` from `NULL` to `TRUE` (confirmed) or `FALSE` (rejected) and persists reviewer notes.
2. **Retraining Trigger** — After every validation write, the system counts rows where `validated IS NOT NULL`; if the count ≥ 50, it logs `RETRAINING_TRIGGERED` and returns a trigger flag.
3. **Leaflet Dashboard** — A Jinja2 + HTMX + Tailwind CSS single-page dashboard with a full-viewport Leaflet map, a sidebar prediction list, and Confirm/Reject buttons that swap updated card fragments without page reload.

## Goals

- Enable field experts to review, confirm, or reject individual predictions through a web interface.
- Persist validation state (`validated` and `validator_notes`) to `invasion_predictions` with clear semantics: `NULL` = pending, `TRUE` = confirmed, `FALSE` = rejected.
- Automatically detect when the reviewed batch reaches the retraining threshold (≥ 50 rows) and emit a structured log event.
- Deliver a desktop expert-review dashboard using the mandated stack (Jinja2 + HTMX + Tailwind CSS + Leaflet) — no client-side frameworks (React/Vue/Svelte).
- Expose a GeoJSON endpoint for full map initialisation and an HTMX-compatible partial rendering workflow for individual prediction cards.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Validate a Single Prediction (Priority: P1)

As a field expert reviewing AI-generated predictions, I need to confirm or reject an individual prediction with optional notes so the system records my assessment and updates the prediction's validation state.

**Why this priority**: Validation is the core HITL action; no retraining or dashboard workflow is meaningful without it.

**Independent Test**: Can be fully tested by calling `PATCH /api/v1/predictions/{id}/validate` with `{"validated": true, "validator_notes": "confirmed via field survey"}` and asserting the row is updated with `validated=TRUE` and the notes persisted.

**Acceptance Scenarios**:

1. **Given** a prediction with `validated=NULL`, **When** `PATCH /api/v1/predictions/{id}/validate` is called with `{"validated": true}`, **Then** the row is updated to `validated=TRUE` and the response returns the updated record.
2. **Given** a prediction with `validated=NULL`, **When** `PATCH /api/v1/predictions/{id}/validate` is called with `{"validated": false, "validator_notes": "misclassified"}`, **Then** the row is updated to `validated=FALSE` with `validator_notes="misclassified"`.
3. **Given** a prediction ID that does not exist, **When** the PATCH endpoint is called, **Then** the API returns `404` with a descriptive error message.
4. **Given** a prediction already validated as `TRUE`, **When** the PATCH endpoint is called with `{"validated": false}`, **Then** the row is updated to `validated=FALSE` (state transitions are allowed in both directions).

---

### User Story 2 — Retraining Trigger Fires at Batch 50 (Priority: P2)

As a system maintainer, I need the platform to automatically detect when enough predictions have been reviewed so the retraining pipeline can be initiated.

**Why this priority**: The retraining trigger is the feedback mechanism that closes the ML lifecycle loop; it depends on User Story 1 being functional.

**Independent Test**: Can be fully tested by mocking 49 and 50 `validated IS NOT NULL` rows in `invasion_predictions` and asserting the trigger returns `False` and `True` respectively.

**Acceptance Scenarios**:

1. **Given** 49 predictions with `validated IS NOT NULL`, **When** a new validation write occurs, **Then** the trigger check returns `False` and no `RETRAINING_TRIGGERED` log is emitted.
2. **Given** 50 predictions with `validated IS NOT NULL`, **When** a new validation write occurs, **Then** the trigger check returns `True` and a `RETRAINING_TRIGGERED` log message is emitted at INFO level.
3. **Given** 51+ predictions with `validated IS NOT NULL`, **When** a new validation write occurs, **Then** the trigger check returns `True` (idempotent — trigger fires on every write once threshold is met).

---

### User Story 3 — Review Predictions on the Dashboard Map (Priority: P3)

As a HITL reviewer, I need a Leaflet map dashboard that displays all predictions as markers and lets me confirm or reject them via a sidebar panel without page reload.

**Why this priority**: The dashboard is the primary user interface for Wave 4; it depends on the validation API (US1) and the GeoJSON prediction endpoint (Wave 3).

**Independent Test**: Can be fully tested by starting the app, navigating to `GET /`, asserting the dashboard HTML renders with Leaflet + HTMX, and verifying that Confirm/Reject button clicks issue PATCH requests and swap updated card fragments.

**Acceptance Scenarios**:

1. **Given** predictions exist in the database, **When** `GET /` is accessed, **Then** a dashboard page renders with a full-viewport Leaflet map and a sidebar panel listing predictions.
2. **Given** the dashboard is loaded, **When** the page initialises, **Then** predictions are fetched from `GET /api/v1/predictions/geojson` and rendered as Leaflet markers.
3. **Given** a prediction card in the sidebar, **When** the Confirm button is clicked, **Then** an HTMX PATCH request is sent to `/api/v1/predictions/{id}/validate` with `{"validated": true}` and the card is swapped with the updated fragment showing "Confirmed".
4. **Given** a prediction card in the sidebar, **When** the Reject button is clicked, **Then** an HTMX PATCH request is sent with `{"validated": false}` and the card is swapped showing "Rejected".

---

### Edge Cases

- Prediction ID in PATCH request is not a valid UUID; the API MUST return `422` (validation error).
- PATCH request body omits the `validated` field; the API MUST return `422` (required field).
- PATCH request body includes `validated` as a non-boolean value; the API MUST return `422`.
- `validator_notes` exceeds a reasonable length (e.g., 1000 characters); the API MUST accept up to the limit and reject with `422` beyond it.
- Dashboard is accessed when zero predictions exist; the map renders with no markers and the sidebar shows "No predictions to review".
- HTMX PATCH request fails due to network error; the card MUST NOT swap and MUST show an error indicator (HTMX `hx-on::after-request` handler).
- Concurrent validation of the same prediction by two reviewers; the last write wins (no optimistic locking in Wave 4; acceptable for single-reviewer MVP).
- Retraining trigger check races with a bulk validation operation; the count query is executed within the same request transaction so the count is consistent.

## Requirements *(mandatory)*

### Functional Requirements

**Validation API**

- **FR-001**: The system MUST expose `PATCH /api/v1/predictions/{id}/validate` that accepts a JSON body with `validated` (boolean, required) and `validator_notes` (string, optional, max 1000 chars).
- **FR-002**: On success, the endpoint MUST update `invasion_predictions.validated` to the provided boolean value and `invasion_predictions.validator_notes` to the provided string (or `NULL` if omitted).
- **FR-003**: The endpoint MUST return `200` with the updated prediction record including `id`, `roi_id`, `species_label`, `confidence`, `hotspot_score`, `model_version`, `validated`, `validator_notes`, and `predicted_at`.
- **FR-004**: The endpoint MUST return `404` when the prediction ID does not exist.
- **FR-005**: The endpoint MUST return `422` when `validated` is missing from the request body or is not a boolean.

**Retraining Trigger**

- **FR-006**: The system MUST implement `check_retrain_trigger()` in `app/services/retrain_trigger.py` that queries `invasion_predictions` for `COUNT(*) WHERE validated IS NOT NULL`.
- **FR-007**: If the count ≥ 50, the function MUST log `RETRAINING_TRIGGERED` at INFO level and return `True`; otherwise it returns `False`.
- **FR-008**: The trigger check MUST be wired into the PATCH validate endpoint and executed after every successful validation write.
- **FR-009**: The trigger response MUST be included in the PATCH endpoint response as a `retraining_triggered: bool` field.

**Dashboard (HTMX + Jinja2 + Leaflet)**

- **FR-010**: The system MUST expose `GET /` that renders `app/templates/dashboard.html` with a full-viewport Leaflet map and an HTMX-powered sidebar panel.
- **FR-011**: The dashboard MUST fetch predictions from `GET /api/v1/predictions/geojson` on page load and render them as Leaflet markers via `L.geoJSON()`.
- **FR-012**: Each prediction in the sidebar MUST be rendered as an HTMX partial (`app/templates/partials/prediction_card.html`) with Confirm and Reject buttons.
- **FR-013**: The Confirm button MUST issue an HTMX `PATCH` to `/api/v1/predictions/{id}/validate` with `{"validated": true}` and swap the response HTML into the card element.
- **FR-014**: The Reject button MUST issue an HTMX `PATCH` with `{"validated": false}` and swap the response HTML into the card element.
- **FR-015**: The system MUST use `GET /api/v1/predictions` (already implemented in Wave 3, returns GeoJSON FeatureCollection) for full map initialisation; no changes required to this endpoint.

### Non-Functional Constraints

- **NFR-001 (Schema Integrity)**: No new columns or tables are introduced in Wave 4; all writes target the existing `invasion_predictions.validated` and `invasion_predictions.validator_notes` columns as defined in `AGENTS.md` Section 4.
- **NFR-002 (Frontend Constraint)**: The dashboard MUST use Jinja2 + HTMX + Tailwind CSS + Leaflet only. No React, Vue, Svelte, or other client-side frameworks are permitted.
- **NFR-003 (Validation Semantics)**: The `validated` column MUST maintain the three-state contract: `NULL` = pending review, `TRUE` = confirmed, `FALSE` = rejected.
- **NFR-004 (Retraining Threshold)**: The retraining trigger threshold of 50 reviewed rows MUST be a module-level constant (`RETRAIN_THRESHOLD = 50`) in `retrain_trigger.py`.
- **NFR-005 (HTMX Resilience)**: HTMX button handlers MUST include error fallbacks so that failed PATCH requests do not silently swap card content.
- **NFR-006 (Latency)**: `PATCH /api/v1/predictions/{id}/validate` SHOULD complete within 500ms for a single-row update under normal operating conditions.
- **NFR-007 (Dashboard Load)**: `GET /` SHOULD render the dashboard shell within 1 second; map marker population via `GET /api/v1/predictions/geojson` SHOULD complete within 2 seconds for ≤ 2,000 predictions.

### Key Entities

- **InvasionPrediction** (`invasion_predictions` table): This feature updates existing rows. Columns modified: `validated` (from `NULL` to `TRUE` or `FALSE`), `validator_notes` (from `NULL` to text). No schema migration is required — the table and columns were created in Wave 1.
- **ValidationRequest** (Pydantic schema): Request body for PATCH endpoint. Fields: `validated` (bool, required), `validator_notes` (str | None, optional, max 1000 chars).
- **ValidationResponse** (Pydantic schema): Response body for PATCH endpoint. Fields: all prediction properties plus `retraining_triggered` (bool).

## Architecture

### Data Flow

```
GET / → dashboard.html
  │
  ├─► Leaflet map initialises
  │     └─► GET /api/v1/predictions/geojson → L.geoJSON(markers)
  │
  └─► Sidebar loads prediction list
        └─► Each prediction_card.html rendered with HTMX buttons

User clicks Confirm/Reject
  │
  ├─► HTMX PATCH /api/v1/predictions/{id}/validate
  │     │
  │     ├─► PATCH handler validates input
  │     ├─► Updates invasion_predictions.validated + validator_notes
  │     ├─► check_retrain_trigger() → COUNT(*) WHERE validated IS NOT NULL
  │     │     └─► If count >= 50: log RETRAINING_TRIGGERED, return True
  │     └─► Returns updated prediction card fragment + retraining_triggered flag
  │
  └─► HTMX swaps response HTML into card element
```

### Out of Scope

- Model retraining execution — the trigger only detects and logs; the actual retraining job is a future wave.
- Multi-reviewer concurrency control — last-write-wins is acceptable for the single-reviewer MVP.
- Authentication / authorization — the dashboard is unprotected in Wave 4 (HITL reviewer is the only role).
- Bulk validation operations — individual confirm/reject only; batch operations are future work.
- Mobile-responsive layout — desktop expert-review dashboard only per `GOALS.md` non-goals.
