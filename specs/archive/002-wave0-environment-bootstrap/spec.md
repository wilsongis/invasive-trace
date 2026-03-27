# Feature Specification: Wave 0 - Environment Bootstrap

**Feature Branch**: `002-wave0-environment-bootstrap`  
**Created**: 2026-03-27  
**Status**: Draft  
**Input**: User description: "Title: Wave 0 - Environment Bootstrap. Purpose: Blocking gate before Wave 1+. Establish minimal runnable FastAPI + PostGIS bootstrap, DB config, Alembic baseline, and NotebookLM grounding connection."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start the Bootstrap Runtime (Priority: P1)

As a contributor beginning work on Invasive Trace, I need a minimal local runtime that starts the application service and PostGIS cleanly so I can verify the project is runnable before any feature work begins.

**Why this priority**: Wave 0 is the gate for every later wave. If the application and spatial database cannot start reliably, no downstream work is safe to begin.

**Independent Test**: Can be fully tested by configuring the required environment variables, running the documented bootstrap command, and confirming the health endpoint responds while only bootstrap routing is exposed.

**Acceptance Scenarios**:

1. **Given** a contributor has the repository and required environment variables configured, **When** the bootstrap startup command is run, **Then** the application service and PostgreSQL 16 + PostGIS 3.4 service start without manual container edits.
2. **Given** the bootstrap runtime is running, **When** the contributor checks the service health endpoint, **Then** the system returns a healthy response from `/healthz`.
3. **Given** the bootstrap runtime is running, **When** the contributor inspects the API surface, **Then** only `/healthz` and bootstrap `/api/v1` routing are present and no business-domain endpoints are exposed.

---

### User Story 2 - Establish the Database Foundation (Priority: P2)

As a contributor preparing the project for later schema work, I need a configured async database layer, a migration baseline, and a smoke test so I can confirm the app can reach PostGIS through the repository-standard configuration.

**Why this priority**: Wave 1 depends on a reliable database session pattern and migration path. Without this baseline, the canonical PostGIS schema cannot be introduced safely.

**Independent Test**: Can be fully tested by loading settings from environment variables, running the migration command against the local database, and executing a smoke test that confirms the app can query `pg_stat_activity`.

**Acceptance Scenarios**:

1. **Given** a valid database connection string is available, **When** the application initializes its database layer, **Then** it creates an async engine, an `AsyncSession` factory, and a request dependency for database access.
2. **Given** the local runtime is available, **When** the migration command is executed, **Then** the Alembic baseline uses the configured database URL and completes without manual connection rewrites.
3. **Given** the migration baseline is configured, **When** the database smoke test runs, **Then** it successfully queries `pg_stat_activity` through the async session path.

---

### User Story 3 - Verify Research Grounding Connectivity (Priority: P3)

As a contributor moving from bootstrap into implementation work, I need the Dev NotebookLM grounding connection verified against the configured gaia-atlas notebook so that Wave 1 begins from the approved research source set.

**Why this priority**: The constitution requires research grounding before pillar work. This is a completion gate for Wave 0, but it is lower priority than getting the runtime and database foundation working.

**Independent Test**: Can be fully tested by running the documented research sync and verification commands, then confirming the local research documents are uploaded to the configured Dev notebook through the NotebookLM UI.

**Acceptance Scenarios**:

1. **Given** the repository is in its Wave 0 state, **When** the NotebookLM sync command is executed, **Then** it targets the Dev notebook identified as `gaia-atlas` with notebook ID `b22e0bd5-8d0b-4173-a447-2b2442430d6e`.
2. **Given** the sync step has completed, **When** the NotebookLM verification command is executed, **Then** the system confirms the Dev grounding connection is live.
3. **Given** the Dev notebook connection is live, **When** the contributor uploads the local research source set through the NotebookLM UI, **Then** Wave 0 grounding is complete and Wave 1 work can begin.

### Edge Cases

- Required environment variables are missing or blank, preventing the app or migration workflow from constructing a valid runtime configuration.
- The application container starts but cannot reach the PostGIS service, causing `/healthz` or the DB smoke test to fail.
- Alembic is initialized but still points to a hard-coded or stale connection string instead of the configured database URL.
- `/api/v1` routing is present but unintentionally exposes business-domain endpoints during Wave 0.
- The bootstrap runtime starts successfully but the lint or test quality gates still fail, so the wave cannot be declared complete.
- NotebookLM sync succeeds but notebook verification fails, leaving research grounding incomplete.
- NotebookLM connection is verified but `/docs/research/` has not been uploaded manually, so the grounding gate remains open.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST provide a minimal application package tree under `app/` containing `__init__.py`, `main.py`, `api/__init__.py`, `api/v1/__init__.py`, `models/__init__.py`, `services/__init__.py`, `ml/__init__.py`, and `scripts/__init__.py`.
- **FR-002**: The system MUST provide a centralized settings module that reads `DATABASE_URL`, `INAT_API_KEY`, `EDDMAPS_API_KEY`, `PC_SDK_SUBSCRIPTION_KEY`, and `LOG_LEVEL` from environment-based configuration.
- **FR-003**: The system MUST provide a database module with an async SQLAlchemy engine, an `AsyncSession` factory, and a reusable `get_db` dependency for FastAPI request handling.
- **FR-004**: The application entrypoint MUST initialize the FastAPI service with lifecycle management, expose `/healthz`, and include bootstrap routing under `/api/v1`.
- **FR-005**: Wave 0 MUST NOT introduce business-domain endpoints beyond `/healthz` and the minimal `/api/v1` bootstrap router wiring.
- **FR-006**: The repository MUST initialize Alembic under `migrations/` and configure both `alembic.ini` and `migrations/env.py` to use the environment-provided database URL.
- **FR-007**: The repository MUST include a database connectivity smoke test in `tests/integration/test_db_connection.py` that confirms the async session path can query `pg_stat_activity`.
- **FR-008**: The container bootstrap workflow MUST allow contributors to start the application service and PostGIS service cleanly through `just start`.
- **FR-009**: The migration workflow MUST allow contributors to run the baseline migration against the local PostGIS instance through `just db-migrate` without manual reconfiguration.
- **FR-010**: Wave 0 completion MUST require `just verify` (lint + test) to finish with zero errors.
- **FR-011**: Wave 0 completion MUST require separate diagnostic runs of `just lint` and `just test` when `just verify` fails.
- **FR-012**: Wave 0 completion MUST require the Dev NotebookLM notebook connection to be synchronized with `just research-sync`, verified with `just research-test`, and grounded with a manual upload of the `/docs/research/` source set.
- **FR-013**: The Wave 0 specification MUST treat the following items as pre-existing grounding context rather than implementation tasks: review-state semantics for `validated`, the spectral band contract, the prediction lineage rule, the synchronous seed endpoint scope, and the configured NotebookLM Dev notebook identity.
- **FR-014**: The application MUST expose an operational root health endpoint (`/healthz`) and MUST enforce `/api/v1` versioning for all feature and business-domain routes.

### Key Entities *(include if feature involves data)*

- **Bootstrap Runtime**: The minimal runnable application and spatial database services that together satisfy the Wave 0 startup gate.
- **Runtime Settings**: Environment-provided configuration values for database connectivity, external API keys, and logging needed to start and validate the bootstrap environment.
- **Database Access Layer**: The async engine, `AsyncSession` factory, and request dependency that establish the single supported path from the application to PostgreSQL 16 + PostGIS 3.4.
- **Migration Baseline**: The Alembic configuration and initial migration environment that will carry the canonical schema in later waves.
- **Research Grounding Connection**: The Dev NotebookLM notebook named `gaia-atlas`, its configured notebook ID, and the uploaded `/docs/research/` source set required before Wave 1 begins.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A contributor can start the local bootstrap environment and receive a healthy response from `/healthz` within 10 minutes of beginning setup, using only the documented repository workflow.
- **SC-002**: The migration baseline and database smoke test both succeed on the local environment without manual edits to connection settings during the validation run.
- **SC-003**: The repository’s Wave 0 quality gate completes with 0 lint errors and 0 test failures.
- **SC-004**: The Dev NotebookLM grounding workflow is verified for 100% of Wave 0 completion attempts before any Wave 1 task is started, evidenced by a checked run log entry in `specs/archive/002-wave0-environment-bootstrap/checklists/requirements.md`.
	- **Completion attempt definition**: One full execution of the Wave 0 validation sequence in `quickstart.md`, from runtime start through research verification and manual source upload confirmation. Any rerun after a failure is a new attempt and requires a separate checklist row.
- **SC-005**: `/healthz` responds with HTTP 200 in under 250ms in local validation runs (measured over 10 requests; p95 <= 250ms).
- **SC-006**: Database smoke test execution against `pg_stat_activity` completes in under 5 seconds per run (measured in CI/local pytest timing output).

## Assumptions

- Wave 0 remains constrained to the constitution-locked stack already established for the project: FastAPI, PostgreSQL 16 + PostGIS 3.4, SQLAlchemy async, GeoAlchemy2, Podman, `uv`, `just`, and Ruff.
- The Dev NotebookLM notebook `gaia-atlas` with ID `b22e0bd5-8d0b-4173-a447-2b2442430d6e` is already defined in project governance documents and does not need to be rediscovered.
- Review-state semantics for `validated`, the spectral band contract, the Stage 2 `model_version` lineage rule, and the synchronous summary scope for observation sync are already reconciled across `AGENTS.md`, the constitution, and `/docs/research/`.
- Contributors performing Wave 0 validation have access to a Podman-capable workstation and the required environment variables or secret values.
- Manual upload of `/docs/research/` through the NotebookLM UI is required to complete grounding, even after automated sync and verification succeed.

## Out of Scope

- ROI CRUD, observation sync business behavior, STAC querying, spectral index calculation, prediction generation, HITL validation flows, and any Wave 1+ capability.
- Creation of business-domain endpoints beyond `/healthz` and minimal bootstrap routing under `/api/v1`.
- Background job orchestration, job-status APIs, and any undocumented asynchronous workflow for seeding or processing.
