# Implementation Plan: Wave 4 — Human-in-the-Loop (HITL) Dashboard

**Branch**: `008-wave4-hitl-dashboard` | **Date**: 2026-04-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-wave4-hitl-dashboard/spec.md`

**Note**: This plan delivers Wave 4 Phases 4A–4C only. It assumes Wave 1 canonical schema and Wave 3 prediction outputs are already in place, and it introduces no schema migrations.

## Summary

Wave 4 implements the human-in-the-loop review workflow that closes the ML lifecycle loop:

1. **Validation API** — `PATCH /api/v1/predictions/{id}/validate` updates `validated` and `validator_notes` on existing prediction rows.
2. **Retraining Trigger** — After every validation write, a count query checks if ≥ 50 rows have been reviewed; if so, it logs `RETRAINING_TRIGGERED`.
3. **Leaflet Dashboard** — A Jinja2 + HTMX + Tailwind CSS single-page dashboard with Leaflet map markers and a sidebar prediction review panel.

No schema migration is required — all writes target existing `invasion_predictions` columns created in Wave 1.

## Technical Context

<!-- Stack is LOCKED — do not change these values without a constitution amendment. -->

**Language/Version**: Python 3.12 (managed by `uv`)
**Primary Dependencies**: FastAPI, SQLAlchemy (async) + GeoAlchemy2, Jinja2, HTMX (client-side script), Tailwind CSS (CDN), Leaflet (CDN), Pydantic
**Storage**: PostgreSQL 16 + PostGIS 3.4 — existing canonical tables only (`invasion_predictions`)
**Testing**: `pytest` + `pytest-asyncio` via `just test`
**Target Platform**: Podman-containerized Linux (macOS dev via `just run`)
**Project Type**: Geospatial AI web service with expert-review dashboard
**Performance Goals**:
- `PATCH /api/v1/predictions/{id}/validate` completes within 500ms for a single-row update.
- `GET /` renders dashboard shell within 1 second; map marker population within 2 seconds for ≤ 2,000 predictions.
**Constraints**:
- No schema/table/column changes in Wave 4; no Alembic migration.
- `validated` maintains three-state contract: `NULL` = pending, `TRUE` = confirmed, `FALSE` = rejected.
- Retraining trigger threshold is a module-level constant (`RETRAIN_THRESHOLD = 50`).
- Dashboard uses Jinja2 + HTMX + Tailwind CSS + Leaflet only — no React/Vue/Svelte.
- All execution paths use FastAPI + async SQLAlchemy + `uv`/`just` workflow.
**Scale/Scope**: Single-reviewer MVP; no authentication, no bulk operations, no mobile layout.

## Constitution Check

*GATE: Must pass before implementation begins. Re-check after detailed design completion.*

Verify ALL of the following before proceeding:

- [ ] **Anti-Context Rot (II)**: Checked `AGENTS.md` Sections 4, 5, 6; schema contracts, API URL contracts, and model versions are sourced verbatim.
- [ ] **Tech Stack (III)**: Plan uses mandated stack only (FastAPI, async SQLAlchemy, PostGIS, Jinja2, HTMX, Tailwind CSS, Leaflet, Ruff, pytest, `uv`, `just`).
- [ ] **Spatial Integrity (IV)**: No schema changes are planned; Wave 4 writes only to existing `invasion_predictions.validated` and `invasion_predictions.validator_notes` columns.
- [ ] **API Resilience (V)**: HTMX button handlers include error fallbacks; PATCH endpoint returns 422 for invalid input.
- [ ] **ML Registry (VI)**: No model version changes; retraining trigger only detects/logs — actual retraining is future work.
- [ ] **Research-First (I)**: Execute `just research-sync` and `just research-test` before coding begins; log result in implementation notes.

*Conclusion: GATE READY FOR IMPLEMENTATION PLANNING. No constitution violations identified.*

## Project Structure

### Documentation (this feature)

```text
specs/008-wave4-hitl-dashboard/
├── spec.md              # Feature specification
├── plan.md              # This file
├── tasks.md             # Follow-on executable task list
└── data-model.md        # Pydantic schemas and data contracts
```

### Source Code (repository root)

```text
app/
├── api/v1/
│   ├── predictions.py              # UPDATE: add PATCH /{id}/validate endpoint
│   └── dashboard.py                # NEW: GET / dashboard route
├── schemas/
│   └── prediction.py               # UPDATE: add ValidationRequest/ValidationResponse schemas
├── services/
│   └── retrain_trigger.py          # NEW: check_retrain_trigger() with COUNT query
├── templates/
│   ├── base.html                   # NEW: Tailwind layout + HTMX + Leaflet CDN includes
│   ├── dashboard.html              # NEW: full-viewport map + HTMX sidebar
│   └── partials/
│       └── prediction_card.html    # NEW: HTMX partial with Confirm/Reject buttons
└── static/
    └── css/
        └── dashboard.css           # NEW: dashboard-specific styles (if needed)

tests/
├── unit/
│   └── test_validate_endpoint.py   # NEW: PATCH validation + 404 + 422 tests
└── unit/
    └── test_retrain_trigger.py     # NEW: threshold count + trigger fire tests
```

**Structure Decision**: Wave 4 adds a thin validation endpoint to the existing predictions router, a new dashboard route for the root path, a retrain trigger service, and Jinja2 templates for the dashboard UI. No new ORM models or migrations are created.

## Implementation Phases (Wave 4)

### Phase 4A — Validation API

**Goal**: Implement `PATCH /api/v1/predictions/{id}/validate` with input validation, DB update, and retraining trigger check.

**Files**:
- `app/api/v1/predictions.py`
- `app/schemas/prediction.py`
- `app/services/retrain_trigger.py`

**Tasks**:
- Add `ValidationRequest` and `ValidationResponse` Pydantic schemas to `app/schemas/prediction.py`:
  - `ValidationRequest`: `validated` (bool, required), `validator_notes` (str | None, optional, max 1000 chars).
  - `ValidationResponse`: all prediction properties + `retraining_triggered` (bool).
- Implement `check_retrain_trigger(db)` in `app/services/retrain_trigger.py`:
  - Query `SELECT COUNT(*) FROM invasion_predictions WHERE validated IS NOT NULL`.
  - If count ≥ `RETRAIN_THRESHOLD` (50), log `RETRAINING_TRIGGERED` at INFO level and return `True`.
  - Otherwise return `False`.
- Implement `PATCH /api/v1/predictions/{id}/validate` in `app/api/v1/predictions.py`:
  - Validate UUID path parameter; return 422 if invalid.
  - Look up prediction by ID; return 404 if not found.
  - Update `validated` and `validator_notes` columns.
  - Call `check_retrain_trigger(db)` and include result in response.
  - Return 200 with `ValidationResponse`.

**Exit Criteria**:
- PATCH endpoint updates `validated` and `validator_notes` correctly.
- 404 returned for unknown ID; 422 returned for missing/invalid `validated`.
- Retraining trigger returns `True` when count ≥ 50, `False` otherwise.
- Unit tests cover all three scenarios.

### Phase 4B — Retraining Trigger

**Goal**: Implement and test the retraining trigger service independently.

**Files**:
- `app/services/retrain_trigger.py`
- `tests/unit/test_retrain_trigger.py`

**Tasks**:
- Define `RETRAIN_THRESHOLD = 50` as a module-level constant.
- Implement `check_retrain_trigger(db: AsyncSession) -> bool` with async COUNT query.
- Log `RETRAINING_TRIGGERED` at INFO level when threshold is met.
- Unit test: mock 49 validated rows → assert `False` returned, no log.
- Unit test: mock 50 validated rows → assert `True` returned, log emitted.
- Unit test: mock 51+ validated rows → assert `True` returned (idempotent).

**Exit Criteria**:
- Trigger function is independently testable with deterministic mock results.
- Log message is emitted only when threshold is met.

### Phase 4C — Leaflet Dashboard (HTMX + Jinja2)

**Goal**: Build the dashboard UI with Leaflet map, HTMX sidebar, and Confirm/Reject workflow.

**Files**:
- `app/templates/base.html`
- `app/templates/dashboard.html`
- `app/templates/partials/prediction_card.html`
- `app/api/v1/dashboard.py`
- `app/main.py` (mount static files + dashboard router)

**Tasks**:
- Create `app/templates/base.html`:
  - HTML5 boilerplate with Tailwind CSS CDN link.
  - HTMX script tag from CDN.
  - Leaflet CSS + JS from CDN.
  - `{% block content %}{% endblock %}` for child templates.
- Create `app/templates/dashboard.html`:
  - Extends `base.html`.
  - Full-viewport Leaflet map div (`#map`).
  - Sidebar div (`#sidebar`) with HTMX `hx-get` to load prediction list.
  - Inline script to fetch `GET /api/v1/predictions` and render `L.geoJSON()` markers.
- Create `app/templates/partials/prediction_card.html`:
  - Renders one prediction with species label, confidence, hotspot score, and validation state.
  - Confirm button: `hx-patch="/api/v1/predictions/{id}/validate"`, `hx-vals='{"validated": true}'`, `hx-swap="outerHTML"`.
  - Reject button: same with `{"validated": false}`.
  - Error fallback: `hx-on::after-request` handler to show error indicator on failure.
- Create `app/api/v1/dashboard.py`:
  - `GET /` route that renders `dashboard.html` via `Jinja2Templates`.
- Wire dashboard router and static files in `app/main.py`.

**Exit Criteria**:
- Dashboard renders at `http://localhost:8000/`.
- Predictions appear as Leaflet markers.
- Confirm/Reject buttons issue PATCH requests and swap updated card fragments.
- Zero predictions → map renders with no markers, sidebar shows "No predictions to review".

### Phase 6 — Polish & Cross-Cutting Concerns

**Purpose**: Execute final quality gate before merge.

**Tasks**:
- Run `just verify` — zero lint errors, zero test failures.
- Verify HTMX error fallbacks work when PATCH endpoint returns 500.
- Verify dashboard shell loads within 1 second with empty prediction set.
- Update `AGENTS.md` Section 9: move Wave 4 tasks to Completed.

**Exit Criteria**:
- `just verify` passes cleanly.
- All acceptance scenarios from spec.md are validated.
