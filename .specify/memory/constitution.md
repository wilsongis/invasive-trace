<!--
Sync Impact Report:
- Version change: 2.0.0 -> 2.0.1
- List of modified principles:
  - I. Research-First Protocol -> I. Remote-Sensing & Research-First Protocol
  - II. The Agent Memory Protocol -> II. The Anti-Context Rot Protocol (Read-Execute-Write)
  - III. Global Tech Stack (NON-NEGOTIABLE) -> III. Global Tech Stack (NON-NEGOTIABLE) [expanded]
  - IV. Universal Command Bridge -> IV. Spatial Data Integrity Contract [replaced]
  - V. Containerized Environment -> V. Resilient-by-Default External API Consumers [replaced]
  - [NEW] VI. ML Model Registry Governance
- Added sections: VI. ML Model Registry Governance (new principle)
- Removed sections: IV. Universal Command Bridge, V. Containerized Environment (merged into III / Additional Constraints)
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ updated (Technical Context locked to stack; Constitution Check gates explicit; Source Code layout uses app/)
  - .specify/templates/spec-template.md ✅ updated (Key Entities references canonical tables; edge cases include API/raster failures; FR prompts include spatial/resilience requirements)
  - .specify/templates/tasks-template.md ✅ updated (Phase 2 uses Alembic/PostGIS/async foundation tasks; Path Conventions use app/ layout)
- Follow-up TODOs:
  - ✅ NotebookLM Notebook ID connected: "gaia-atlas" (b22e0bd5-8d0b-4173-a447-2b2442430d6e)
  - ✅ Grounding fixes applied for review-state semantics, spectral band contract, and prediction lineage
-->
# Invasive Trace Constitution

## Core Principles

### I. Remote-Sensing & Research-First Protocol
All spectral analysis decisions and ML pipeline choices MUST be grounded in documents
located in `/docs/research/` or the linked NotebookLM notebook ("gaia-atlas").
Experimental remote sensing pipelines MUST use
the Dev notebook only; run `just research-sync` to initialize the MCP connection,
`just research-test` to verify it, and upload local research sources through the
NotebookLM UI before beginning any new pillar of work. Promotion to the Prod notebook
is ONLY permitted once an SRS pillar has been declared finalized and its Success
Criteria verified.

**Rationale:** Multi-temporal spectral analysis and ecological ML are high-complexity
domains where undocumented assumptions propagate silently. Anchoring every decision
in versioned research documents prevents model drift and preserves scientific
reproducibility for the Southern Grassland Institute.

### II. The Anti-Context Rot Protocol (Read-Execute-Write)
Before starting ANY task, an agent MUST read `AGENTS.md` Sections 4 (PostGIS schema),
5 (API contracts), and 6 (ML model registry) in full. Agents MUST NOT guess, infer,
or cache schema column names, external API URLs, or model version strings — every
reference MUST be verified against the current `AGENTS.md`. After every architectural
decision or pillar completion, the agent MUST update the relevant section of `AGENTS.md`
before concluding the session.

Anti-context-rot rules (non-negotiable):
- Never guess schema column names — check `AGENTS.md` Section 4.
- Never hard-code or infer API URLs — check `AGENTS.md` Section 5.
- Never reference a model by name without confirming the version string from
  `AGENTS.md` Section 6.

**Rationale:** Context rot — stale column names, wrong API paths, mismatched model
versions — is the single largest source of production bugs in AI-assisted codebases.
This protocol makes rot structurally impossible.

### III. Global Tech Stack (NON-NEGOTIABLE)
The following technology choices are locked. Deviations MUST NOT be introduced without
an explicit decision recorded in `AGENTS.md` and a constitution amendment.

| Layer | Mandated Technology | Hard Prohibition |
| :--- | :--- | :--- |
| Backend | FastAPI + Python 3.12 | No Django, Flask |
| Package Manager | `uv` exclusively | No pip, poetry |
| Database | PostgreSQL 16 + PostGIS 3.4 | No SQLite, MongoDB |
| ORM / Spatial | SQLAlchemy (async) + GeoAlchemy2 | No raw psycopg2 geometry strings |
| Frontend | Jinja2 + HTMX + Tailwind CSS | No React, Vue, Svelte |
| Raster I/O | Rasterio + GDAL (via Containerfile) | COG-native reads only |
| Remote Sensing | pystac-client + planetary-computer | STAC v1 catalog queries only |
| ML: Classical | Scikit-learn (RandomForest / XGBoost) | No model zoo shortcuts |
| ML: Deep | PyTorch (U-Net architecture) | No TensorFlow / Keras |
| Container | Podman + Containerfile | No Docker Desktop |
| Automation | `just` command runner | No Makefile, shell scripts as entry points |
| Linting | Ruff | No flake8, black, pylint |

All REST endpoints MUST be versioned under `/api/v1/`. API keys MUST be read exclusively
from environment variables and MUST NEVER be hardcoded, logged, or interpolated into
strings that appear in logs.

**Rationale:** A single coherent stack eliminates toolchain fragmentation, makes
onboarding deterministic, and ensures the geospatial and ML dependency graph remains
reproducible across macOS and containerized CI environments.

### IV. Spatial Data Integrity Contract
The four canonical PostGIS tables are contract-locked:

- `regions_of_interest`
- `invasion_predictions`
- `ground_truth_observations`
- `spectral_time_series`

The following rules are NON-NEGOTIABLE:
- Column names and geometry types in these tables MUST NOT be altered without both a
  new Alembic schema migration (`just db-migrate`) AND a corresponding update to
  `AGENTS.md` Section 4.
- All geometry columns MUST use SRID 4326 (WGS84). No other SRID is permitted for
  storage; reproject at ingest if necessary.
- The `confidence` column in `invasion_predictions` MUST enforce the DB-layer
  constraint `CHECK (confidence BETWEEN 0.0 AND 1.0)`. This constraint MUST NOT be
  removed or relaxed.
- The `validated` column in `invasion_predictions` MUST remain nullable with
  tri-state semantics: `NULL = pending review`, `TRUE = confirmed`, `FALSE = rejected`.
  New predictions MUST be inserted with `validated = NULL` until a HITL reviewer acts.
- Raster outputs MUST be COG-compatible (Cloud-Optimized GeoTIFF). No other raster
  storage format is permitted.

**Rationale:** Spatial data schema drift causes silent coordinate corruption and
breaks downstream ML feature vectors. A contract lock makes every schema change a
deliberate, reviewed act rather than an accidental migration.

### V. Resilient-by-Default External API Consumers
All code that calls Planetary Computer, iNaturalist, EDDMapS, or USGS 3DEP MUST
implement the following failure-handling contract — no exceptions:

1. **Rate limiting (HTTP 429):** Exponential backoff with a maximum of 3 retries.
   After 3 failures the request MUST be logged and skipped; it MUST NOT raise an
   unhandled exception.
2. **Missing tiles / partial STAC results:** Log the missing item ID at WARN level
   and continue processing remaining items. Never raise on a partial result set.
3. **Cloud-masked scenes:** Any scene where `cloud_cover > 0.20` MUST be persisted
   with `is_masked = TRUE` in `spectral_time_series` and excluded from all spectral
   index computation (NDVI, ENDVI, Red-Edge).
4. **Band contract:** Sentinel-2 spectral work MUST use B08/B04 for NDVI, B08/B04/B03
  for ENDVI, and the red-edge bands (B05/B8A as required by the chosen formula)
  for red-edge metrics. Band selections MUST be documented in research artifacts.

No external-API-facing function may propagate an unhandled exception to the FastAPI
request lifecycle. All API keys MUST be sourced from environment variables
(`INAT_API_KEY`, `EDDMAPS_API_KEY`).

**Rationale:** Satellite imagery pipelines are inherently unreliable — partial STAC
results, transient 429s, and cloud contamination are the norm, not the exception.
Fail-safe defaults protect the completeness of stored spectral time series.

### VI. ML Model Registry Governance
All three pipeline stages MUST reference models by the exact version strings recorded
in `AGENTS.md` Section 6:

| Stage | Model | Current Version |
| :--- | :--- | :--- |
| Stage 1 | `AnomalyDetector` | `anomaly-v0.1.0` |
| Stage 2 | `FocalClassifier` | `rf-v0.1.0` |
| Stage 3 | `UNetTexture` | `unet-v0.1.0` |

Rules:
- Model artifacts MUST be stored at `./models/{model_name}/{version}/`.
- Retraining MUST NOT be triggered until the HITL feedback batch reaches ≥ 50
  confirmed or rejected predictions.
- Any new model version MUST be registered in `AGENTS.md` Section 6 before it is
  referenced in code.
- The `model_version` column in `invasion_predictions` MUST exactly match a
  registered registry version string and stores the Stage 2 classifier version used
  to assign `species_label` + `confidence`.
- Pipeline lineage for Stage 1 and Stage 3 MUST be preserved in logs or sidecar
  metadata if a single `model_version` column is retained.

**Rationale:** Untracked model versions make audit trails impossible and break the
Southern Grassland Institute's scientific reproducibility requirements.

## Additional Constraints

- `AGENTS.md` is the single source of truth for project state, schema, API contracts,
  and ML registry. It supersedes all other documentation.
- `just verify` (lint + test suite) MUST pass with zero errors before any architectural
  change is merged or any `AGENTS.md` section is updated.
- All containerized services MUST be managed via Podman Compose (`just start`).
  Direct `docker` commands are prohibited.
- Token optimization: load context in cache-aware order — `constitution.md` →
  `STACK.md` → `AGENTS.md` → plan/spec → execution logs. Never inject session IDs
  or timestamps above the cache boundary.

## Development Workflow

1. **READ**: Read `AGENTS.md` Sections 4, 5, and 6 before any feature work begins.
2. **SYNC**: Initialize and verify the Dev NotebookLM connection with `just research-sync` and `just research-test`, then upload `/docs/research/` sources in the NotebookLM UI.
3. **SPECIFY**: Open or update the feature spec with `/speckit.specify`.
4. **PLAN**: Create the execution plan with `/speckit.plan`.
5. **EXECUTE**: Implement using the mandated Global Tech Stack (Section III).
6. **VERIFY**: Run `just verify` (lint + tests) — zero errors required.
7. **WRITE**: Update `AGENTS.md` with architectural decisions before concluding.

## Governance

This Constitution and `AGENTS.md` jointly supersede all other project practices,
coding conventions, and verbal agreements. Any amendment to this Constitution requires:

1. A version bump following semantic versioning (MAJOR: principle removal/redefinition;
   MINOR: new principle or material expansion; PATCH: wording/clarification).
2. An updated Sync Impact Report in the HTML comment block at the top of this file.
3. A propagation check across `.specify/templates/` files for alignment.
4. A commit message of the form:
   `docs: amend constitution to vX.Y.Z (<summary of changes>)`

All pull requests and agent task sessions MUST verify compliance with the Global Tech
Stack (Section III), the Spatial Data Integrity Contract (Section IV), and the
Anti-Context Rot Protocol (Section II) before marking work complete.

**Version**: 2.0.1 | **Ratified**: 2026-03-27 | **Last Amended**: 2026-03-27
