# Tasks: Wave 0 - Environment Bootstrap

**Input**: Design documents from `/specs/archive/002-wave0-environment-bootstrap/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Tests are required for this feature because the spec explicitly requires a health endpoint validation path and a database smoke test through `just test`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Invasive Trace canonical layout**: `app/api/v1/`, `app/models/`, `app/services/`, `app/ml/`, `app/scripts/`
- **Tests**: `tests/unit/`, `tests/integration/`
- **Migrations**: `migrations/` (Alembic)
- **Model artifacts**: `models/{model_name}/{version}/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Bootstrap the package layout and repo-level configuration required before runtime and DB work can begin.

- [X] T001 Create the Wave 0 package skeleton in `app/__init__.py`, `app/api/__init__.py`, `app/api/v1/__init__.py`, `app/models/__init__.py`, `app/services/__init__.py`, `app/ml/__init__.py`, and `app/scripts/__init__.py`
- [X] T002 Update Wave 0 runtime dependencies in `pyproject.toml` for FastAPI bootstrap, async SQLAlchemy/PostGIS access, Alembic, and test support
- [X] T003 [P] Validate bootstrap environment defaults in `.env.example` for `DATABASE_URL`, `INAT_API_KEY`, `EDDMAPS_API_KEY`, `PC_SDK_SUBSCRIPTION_KEY`, and `LOG_LEVEL`
- [X] T004 [P] Verify Wave 0 command bridge coverage in `justfile` and `compose.yml` for `just start`, `just db-migrate`, `just research-sync`, and `just research-test`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core runtime and migration infrastructure that MUST be complete before any user story implementation can begin.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Create centralized settings loading in `app/config.py` using environment-backed configuration for all Wave 0 runtime values
- [X] T006 [P] Create the async database access layer in `app/db.py` with engine creation, `AsyncSession` factory, and `get_db` dependency
- [X] T007 Create the bootstrap FastAPI app and versioned router wiring in `app/main.py` and `app/api/v1/__init__.py`
- [X] T008 [P] Initialize Alembic configuration in `alembic.ini` and `migrations/env.py` so migrations resolve `DATABASE_URL` from runtime settings
- [X] T009 Create the baseline migration scaffold under `migrations/versions/` with no Wave 1 domain schema tables

**Checkpoint**: Foundation ready — Wave 0 user story implementation can now proceed.

---

## Phase 3: User Story 1 - Start the Bootstrap Runtime (Priority: P1) 🎯 MVP

**Goal**: Contributors can start the app service and PostGIS locally and verify a healthy bootstrap runtime.

**Independent Test**: Configure env vars, run `just start`, and confirm `/healthz` responds while only bootstrap `/api/v1` routing is present.

### Tests for User Story 1

- [X] T010 [P] [US1] Create bootstrap runtime integration coverage in `tests/integration/test_healthz.py` for `/healthz` and bootstrap-only API exposure
- [X] T025 [P] [US1] Add latency assertion tooling in `tests/integration/test_healthz.py` to measure 10 requests and validate p95 <= 250ms during local validation

### Implementation for User Story 1

- [X] T011 [US1] Implement the `/healthz` endpoint and lifespan-safe startup/shutdown flow in `app/main.py`
- [X] T012 [US1] Restrict bootstrap routing to minimal `/api/v1` wiring in `app/api/v1/__init__.py`
- [X] T013 [US1] Validate container startup behavior in `compose.yml` and `justfile` so `just start` brings up the app and PostGIS cleanly without manual edits

**Checkpoint**: User Story 1 is complete when the local bootstrap runtime starts and the health endpoint passes.

---

## Phase 4: User Story 2 - Establish the Database Foundation (Priority: P2)

**Goal**: Contributors can reach PostGIS through the async app path, run a migration baseline, and verify connectivity via tests.

**Independent Test**: Run `just db-migrate` and `just test`; confirm the smoke test queries `pg_stat_activity` through the async session path.

### Tests for User Story 2

- [X] T014 [P] [US2] Create the database connectivity smoke test in `tests/integration/test_db_connection.py` to query `pg_stat_activity` through the async session path
- [X] T026 [P] [US2] Add execution-timing assertion or pytest timing capture in `tests/integration/test_db_connection.py` to validate runtime <= 5s

### Implementation for User Story 2

- [X] T015 [US2] Wire `DATABASE_URL` resolution from `app/config.py` into `alembic.ini` and `migrations/env.py`
- [X] T016 [US2] Integrate the database session dependency into the bootstrap runtime in `app/db.py` and `app/main.py`
- [X] T017 [US2] Create and validate the Wave 0 Alembic baseline revision in `migrations/versions/`

**Checkpoint**: User Story 2 is complete when migrations run without manual rewrites and the DB smoke test passes.

---

## Phase 5: User Story 3 - Verify Research Grounding Connectivity (Priority: P3)

**Goal**: Contributors can verify the Dev NotebookLM connection for `gaia-atlas` and complete the research grounding gate before Wave 1.

**Independent Test**: Run `just research-sync`, run `just research-test`, then upload `/docs/research/` in NotebookLM UI using the documented workflow.

### Implementation for User Story 3

- [X] T018 [US3] Verify the Dev NotebookLM workflow is accurately documented in `specs/archive/002-wave0-environment-bootstrap/quickstart.md` and `AGENTS.md`
- [X] T019 [US3] Validate the MCP connection workflow against `justfile` and `AGENTS.md` using `just research-sync`, `just research-test`, and `just research-open`
- [ ] T020 [US3] Record SC-004 research-grounding evidence per completion attempt in `specs/archive/002-wave0-environment-bootstrap/checklists/requirements.md` (`attempt_id`, date, operator, `just research-sync` result, `just research-test` result, manual `/docs/research/` upload confirmation)

**Checkpoint**: User Story 3 is complete when the Dev notebook connection is verified and the research source set is uploaded.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final Wave 0 validation and state updates before Wave 1 can begin.

- [X] T021 [P] Run `just verify` and resolve Wave 0 failures across `app/main.py`, `app/config.py`, `app/db.py`, `tests/integration/test_healthz.py`, and `tests/integration/test_db_connection.py`
- [X] T022 If `just verify` fails, run `just lint` and `just test` separately to isolate failures and apply targeted fixes
- [ ] T023 Run `just db-migrate` and `just start` and confirm runtime + migration readiness before final quality gate
- [ ] T024 Run the validation sequence from `specs/archive/002-wave0-environment-bootstrap/quickstart.md` end-to-end and confirm Wave 0 completion criteria are satisfied
- [X] T028 Add explicit FR-013 governance validation note in `specs/archive/002-wave0-environment-bootstrap/checklists/requirements.md` confirming pre-existing grounding context was not reimplemented in Wave 0
- [ ] T029 Update completion state in `AGENTS.md` and `TODO.md` only after `just verify` passes and all Wave 0 evidence artifacts are complete
- [ ] T030 Capture SC-001 setup-to-health elapsed time evidence in `specs/archive/002-wave0-environment-bootstrap/checklists/requirements.md` and verify completion in <= 10 minutes using the `quickstart.md` validation sequence

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion and benefits from User Story 1 runtime work
- **User Story 3 (Phase 5)**: Depends on Setup/command-bridge readiness and may proceed after Foundational completion
- **Polish (Phase 6)**: Depends on all Wave 0 user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: First deliverable — establishes the runnable bootstrap environment
- **User Story 2 (P2)**: Depends on the runtime and foundational config being present
- **User Story 3 (P3)**: Depends on the documented MCP workflow and completion-state recording paths

### Within Each User Story

- Tests before implementation where a test artifact is specified
- Runtime/config before migrations
- Migrations before end-to-end validation
- Documentation/state updates after successful validation

### Parallel Opportunities

- `T003` and `T004` can run in parallel during Setup
- `T006` and `T008` can run in parallel during Foundational work
- `T010` and `T014` can be prepared in parallel once the foundation exists
- `T025` and `T026` can run in parallel while finalizing performance evidence

---

## Parallel Example: Wave 0 Foundation

```bash
# Parallelizable after T001-T002
T003: validate .env.example defaults
T004: verify justfile + compose.yml bootstrap commands

# Parallelizable after setup
T006: create app/db.py async session layer
T008: configure alembic.ini + migrations/env.py
```

---

## Implementation Strategy

### MVP First

1. Complete Phases 1-3 to get a runnable bootstrap runtime with `/healthz`
2. Complete Phase 4 to establish the migration and DB test baseline
3. Complete Phase 5 to verify research grounding
4. Finish Phase 6 and only then begin Wave 1

### Incremental Delivery

- Deliver User Story 1 first so contributors can start the system
- Add User Story 2 second so schema work has a safe DB path
- Finish with User Story 3 so research grounding is verified before feature implementation
