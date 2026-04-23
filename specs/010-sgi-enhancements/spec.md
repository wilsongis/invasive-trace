# SGI Way Enhancements Specification

## Overview
The **SGI Way** defines six guiding pillars for grassland restoration projects.  These pillars are treated as **non‑functional requirements (NFRs)** that shape the design, implementation, and operation of the Invasive‑Trace platform.

| Pillar | Description |
|--------|-------------|
| **Standardized** | Develop restoration practices that are appropriate for the landscape and can be expressed as reusable, versioned protocols. |
| **Provable** | Quantify ecological improvement resulting from projects through measurable key performance indicators (KPIs). |
| **Repeatable** | Ensure the same results are achieved regardless of the team executing the project by enforcing deterministic pipelines and provenance tracking. |
| **Efficient** | Use time‑saving approaches, async processing, and ergonomic UI to achieve faster outcomes without staff burnout. |
| **Scalable** | Enable massive increase in impacted acreage while maintaining quality via tiling, sharding, and horizontal service scaling. |
| **Innovative** | Provide a sandbox for testing new ideas, models, and workflows, and incorporate successful innovations into the main pipeline. |

## Non‑Functional Requirements

### 1. Standardized
* **Requirement**: All restoration workflows must be defined in a `restoration_protocols` table (see Data Model). Each protocol is versioned and referenced by predictions.
* **Success Criteria**: Adding a new protocol does not require code changes; the API can create, read, update, and delete protocols via `/api/v1/protocols`.

### 2. Provable
* **Requirement**: The system must emit KPI metrics for each project (e.g., restored area, vegetation index improvement).
* **Success Criteria**: A `/api/v1/metrics` endpoint returns JSON with fields `project_id`, `restored_acres`, `ndvi_improvement`, `confidence_mean`.

### 3. Repeatable
* **Requirement**: All ML pipelines run with a fixed random seed and log the exact model version, hyper‑parameters, and input data hash.
* **Success Criteria**: Re‑running a pipeline on the same input data produces identical predictions (bit‑wise equality).

### 4. Efficient
* **Requirement**: Batch jobs are processed asynchronously with a configurable concurrency limit (`MAX_CONCURRENT_JOBS`). UI shortcuts for common tasks are provided.
* **Success Criteria**: End‑to‑end processing time for a typical ROI batch (< 10 km²) is ≤ 5 minutes on the reference hardware.

### 5. Scalable
* **Requirement**: Spatial processing is tiled; each tile can be processed independently and in parallel. The service can be horizontally scaled via Podman compose.
* **Success Criteria**: System can handle a simultaneous load of 100 ROIs without degradation of response latency (> 200 ms).

### 6. Innovative
* **Requirement**: A plug‑in framework (`app/plugins/`) allows experimental model modules to be discovered at runtime. A sandbox endpoint `/api/v1/sandbox/run` executes a selected plug‑in on supplied data.
* **Success Criteria**: New plug‑in can be added without modifying core code and is runnable via the sandbox endpoint.

## Architecture Impact
* **Database** – New `restoration_protocols` table (see Data Model).
* **API** – Endpoints for protocols, metrics, and sandbox.
* **Pipeline** – Deterministic runner wrapper, provenance logger, and plug‑in loader.
* **Configuration** – New settings in `app/config.py` for concurrency, tiling size, and random seed.

## Acceptance Tests (High‑Level)
1. Create a protocol via API and verify it appears in the DB.
2. Run a deterministic pipeline on a sample ROI and confirm identical output on repeat runs.
3. Query `/api/v1/metrics` after a completed project and validate KPI fields.
4. Deploy two service instances behind a load balancer and confirm load handling.
5. Add a dummy plug‑in and execute it through the sandbox endpoint.

## Dependencies
* Existing FastAPI stack (see `AGENTS.md`).
* PostgreSQL 16 with PostGIS for spatial tiling.
* `uv` for dependency management.

## Open Questions
* Desired granularity for KPI metrics (per ROI vs per project).
* Maximum allowed tile size for scalability tests.

---
*Document generated on 2026‑04‑23.*
