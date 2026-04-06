# Tasks: Wave 4 — Human-in-the-Loop (HITL) Dashboard

**Input**: Design documents from `/specs/008-wave4-hitl-dashboard/`
**Prerequisites**: `plan.md` (required), `spec.md` (required)

**Tests**: Tests are required for this feature because the specification defines mandatory independent test criteria and acceptance scenarios for each user story.

**Organization**: Tasks are grouped by user story to keep each increment independently testable and dependency-ordered.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`US1`, `US2`, `US3`)
- Include exact file paths in every task description

## Phase 0: Research Preflight

**Purpose**: Satisfy the constitution's research-first gate before implementation begins.

- [ ] W4-T001 Execute `just research-sync` and `just research-test` from repository root (`justfile`) and record the outcome or manual-login blocker in `AGENTS.md`

---

## Phase 1: Setup (Shared Scaffolding)

**Purpose**: Create Wave 4 module and test scaffolding before foundational service implementation.

- [ ] W4-T002 Create Wave 4 scaffolding files `app/services/retrain_trigger.py`, `app/api/v1/dashboard.py`, `app/templates/base.html`, `app/templates/dashboard.html`, `app/templates/partials/prediction_card.html`, and `tests/unit/test_validate_endpoint.py`, `tests/unit/test_retrain_trigger.py`
- [ ] W4-T003 [P] Register Wave 4 routers in `app/api/v1/__init__.py` and wire dashboard static files + router in `app/main.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared validation schemas and retraining trigger service required by all user stories.

**CRITICAL**: Complete this phase before user story implementation.

- [ ] W4-T004 Add `ValidationRequest` and `ValidationResponse` Pydantic schemas to `app/schemas/prediction.py` — `ValidationRequest` with `validated` (bool, required) and `validator_notes` (str | None, optional, max 1000 chars); `ValidationResponse` with all prediction properties plus `retraining_triggered` (bool)
- [ ] W4-T005 [P] Implement `check_retrain_trigger(db: AsyncSession) -> bool` in `app/services/retrain_trigger.py` with `RETRAIN_THRESHOLD = 50` constant, async COUNT query on `validated IS NOT NULL`, and INFO-level `RETRAINING_TRIGGERED` log when threshold is met

**Checkpoint**: Schemas and trigger service are ready for endpoint and dashboard wiring.

---

## Phase 3: User Story 1 — Validate a Single Prediction (Priority: P1) 🎯 MVP

**Goal**: Implement `PATCH /api/v1/predictions/{id}/validate` to update validation state and trigger retraining check.

**Independent Test**: Call `PATCH /api/v1/predictions/{id}/validate` with `{"validated": true, "validator_notes": "confirmed"}` and assert the row is updated with `validated=TRUE` and notes persisted; assert 404 for unknown ID.

### Tests for User Story 1

- [ ] W4-T006 [P] [US1] Add unit tests in `tests/unit/test_validate_endpoint.py` — assert PATCH sets `validated=TRUE` and persists `validator_notes`; assert 404 for unknown ID; assert 422 for missing `validated` field; assert 422 for non-boolean `validated`

### Implementation for User Story 1

- [ ] W4-T007 [US1] Implement `PATCH /api/v1/predictions/{id}/validate` endpoint in `app/api/v1/predictions.py` — validate UUID, look up prediction, update `validated` + `validator_notes`, call `check_retrain_trigger`, return 200 with `ValidationResponse`

**Checkpoint**: Validation endpoint updates prediction rows and returns retraining trigger status.

---

## Phase 4: User Story 2 — Retraining Trigger Fires at Batch 50 (Priority: P2)

**Goal**: Validate the retraining trigger independently with mock row counts.

**Independent Test**: Mock 49 and 50 `validated IS NOT NULL` rows and assert the trigger returns `False` and `True` respectively.

### Tests for User Story 2

- [ ] W4-T008 [P] [US2] Add unit tests in `tests/unit/test_retrain_trigger.py` — mock 49 validated rows → assert `False` returned, no log; mock 50 validated rows → assert `True` returned, `RETRAINING_TRIGGERED` log emitted; mock 51+ rows → assert `True` (idempotent)

**Checkpoint**: Retraining trigger is independently testable and correctly fires at threshold.

---

## Phase 5: User Story 3 — Review Predictions on the Dashboard Map (Priority: P3)

**Goal**: Build the Leaflet + HTMX dashboard with Confirm/Reject workflow.

**Independent Test**: Start the app, navigate to `GET /`, assert dashboard HTML renders with Leaflet + HTMX, and verify Confirm/Reject button clicks issue PATCH requests and swap updated card fragments.

### Implementation for User Story 3

- [ ] W4-T009 [US3] Create `app/templates/base.html` — HTML5 boilerplate with Tailwind CSS CDN, HTMX script CDN, Leaflet CSS + JS CDN, and `{% block content %}` slot
- [ ] W4-T010 [US3] Create `app/templates/dashboard.html` — extends `base.html`; full-viewport Leaflet map div; HTMX sidebar panel; inline script to fetch `GET /api/v1/predictions/geojson` and render `L.geoJSON()` markers; empty-state message when no predictions exist
- [ ] W4-T011 [US3] Create `app/templates/partials/prediction_card.html` — renders prediction with species label, confidence, hotspot score, validation state; Confirm button with `hx-patch` + `hx-vals='{"validated": true}'` + `hx-swap="outerHTML"`; Reject button with same for `false`; `hx-on::after-request` error fallback
- [ ] W4-T012 [US3] Create `GET /` route in `app/api/v1/dashboard.py` — renders `dashboard.html` via `Jinja2Templates`; wire static file serving and dashboard router in `app/main.py`

**Checkpoint**: Dashboard renders at `http://localhost:8000/`; predictions appear as map markers; Confirm/Reject updates card via HTMX without page reload.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Execute final quality gate before merge.

- [ ] W4-T013 Execute full verification gate with `just verify` from repository root (`justfile`) and resolve any regressions in `app/api/v1/`, `app/services/`, `app/schemas/`, `app/templates/`, and `tests/`
- [ ] W4-T014 Update `AGENTS.md` Section 9: move Wave 4 tasks to Completed; update status line

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 0 (Research Preflight)**: No dependencies; must complete before implementation begins.
- **Phase 1 (Setup)**: Depends on Phase 0.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US2)**: Depends on Phase 2 (trigger service); can run in parallel with Phase 3.
- **Phase 5 (US3)**: Depends on Phase 3 (validation endpoint) and Wave 3 (`GET /api/v1/predictions/geojson`).
- **Phase 6 (Polish)**: Depends on completion of all user stories.

### User Story Dependencies

- **US1 (P1)**: MVP and first deliverable — validation endpoint.
- **US2 (P2)**: Depends on Phase 2 trigger service; independently testable with mocks.
- **US3 (P3)**: Depends on US1 endpoint being functional for HTMX button wiring.

### Parallel Opportunities

- Setup: `W4-T003` can run in parallel after `W4-T002` scaffolding exists.
- Foundational: `W4-T004` and `W4-T005` can run in parallel (schemas vs service).
- US1: `W4-T006` tests can run in parallel with `W4-T007` implementation after schemas are defined.
- US2: `W4-T008` is independently testable once `W4-T005` trigger service exists.

---

## Parallel Example: User Story 1

```bash
Task: "W4-T006 [US1] Add unit tests for PATCH /api/v1/predictions/{id}/validate in tests/unit/test_validate_endpoint.py"
Task: "W4-T007 [US1] Implement PATCH /api/v1/predictions/{id}/validate endpoint in app/api/v1/predictions.py"
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Research Preflight (Phase 0), Setup (Phase 1), and Foundational work (Phase 2).
2. Deliver and validate US1 validation endpoint behavior.
3. Use US1 outputs to enable trigger testing and dashboard workflow.

### Incremental Delivery

1. Complete research preflight and record status.
2. Deliver validation API + retraining trigger (US1 + US2).
3. Deliver Leaflet + HTMX dashboard (US3).
4. Run final quality gate (`just verify`) before merge.

---

## Completion Criteria

- `PATCH /api/v1/predictions/{id}/validate` is implemented in `app/api/v1/predictions.py` with `ValidationRequest`/`ValidationResponse` schemas in `app/schemas/prediction.py`.
- `check_retrain_trigger()` is implemented in `app/services/retrain_trigger.py` with `RETRAIN_THRESHOLD = 50` and `RETRAINING_TRIGGERED` log emission.
- Dashboard renders at `GET /` with Leaflet map, HTMX sidebar, and Confirm/Reject buttons that swap updated card fragments.
- Required unit tests are added in `tests/unit/test_validate_endpoint.py` and `tests/unit/test_retrain_trigger.py`.
- Full quality gate `just verify` passes from repository root.
- `AGENTS.md` Section 9 is updated to reflect Wave 4 completion.
