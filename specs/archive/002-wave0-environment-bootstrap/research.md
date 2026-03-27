# Research Notes: Wave 0 - Environment Bootstrap

## Objective

Define the minimal technical shape required before Wave 1 can safely introduce the canonical PostGIS schema and domain endpoints.

## Confirmed Inputs

- `AGENTS.md` is the single source of truth for schema, API contracts, model registry, and project state.
- The project stack is locked to FastAPI, PostgreSQL 16 + PostGIS 3.4, SQLAlchemy async, GeoAlchemy2, Podman, `uv`, `just`, and Ruff.
- NotebookLM grounding uses the Dev notebook `gaia-atlas` and is completed through MCP init/test plus manual source upload.

## Decisions

### 1. Bootstrap-only FastAPI surface

Wave 0 exposes only:

- `GET /healthz`
- versioned bootstrap routing under `/api/v1`

No ROI, observation, STAC, prediction, or HITL endpoints are created in this wave.

### 2. Database-first access path

Wave 0 establishes one supported DB access pattern:

- async engine
- `AsyncSession` factory
- FastAPI `get_db` dependency

This prevents later waves from introducing multiple DB connection styles.

### 3. Alembic baseline before schema implementation

Wave 0 creates migration plumbing only. The canonical four tables are intentionally deferred to Wave 1 so the migration system exists before contract-locked schema changes begin.

### 4. Research grounding is a completion gate, not a side task

Wave 0 is incomplete unless:

- the MCP connection is initialized to `gaia-atlas`
- the connection is verified
- `/docs/research/` is uploaded manually in NotebookLM UI

## Rejected Alternatives

### Add Wave 1 tables in Wave 0

Rejected because it collapses bootstrap and schema implementation into one step and weakens the blocking-gate purpose of Wave 0.

### Expose real feature endpoints during bootstrap

Rejected because the spec explicitly limits Wave 0 to runtime verification and bootstrap routing only.

### Use ad hoc shell DB checks instead of a pytest smoke test

Rejected because the repository standard requires verification through `just test` and reusable test artifacts.

## Open Constraints

- Podman compose must be the supported local runtime path.
- Settings must resolve from environment variables only.
- Business-domain work starts in Wave 1, not earlier.
