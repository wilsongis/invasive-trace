# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!-- Stack is LOCKED — do not change these values without a constitution amendment. -->

**Language/Version**: Python 3.12 (managed by `uv`)
**Primary Dependencies**: FastAPI, SQLAlchemy (async) + GeoAlchemy2, Rasterio, pystac-client, planetary-computer, scikit-learn, XGBoost, PyTorch (U-Net)
**Storage**: PostgreSQL 16 + PostGIS 3.4 — four canonical tables: `regions_of_interest`, `invasion_predictions`, `ground_truth_observations`, `spectral_time_series`
**Testing**: `pytest` + `pytest-asyncio` via `just test`
**Target Platform**: Podman-containerized Linux (macOS dev via `just run`)
**Project Type**: Geospatial AI web service
**Performance Goals**: [feature-specific — e.g., STAC query < 5s for 1-year time range, inference < 2s per ROI]
**Constraints**: COG-native raster reads only; all geometries SRID 4326; `confidence` constrained 0.0–1.0 at DB layer; API keys from env vars only
**Scale/Scope**: [feature-specific — e.g., ROI count, scene count, prediction volume]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify ALL of the following before proceeding:

- [ ] **Anti-Context Rot (II)**: Checked `AGENTS.md` Sections 4, 5, 6 — no schema column names, API URLs, or model versions guessed.
- [ ] **Tech Stack (III)**: Feature uses only mandated stack (FastAPI, uv, PostGIS, SQLAlchemy async, Rasterio/COG, pystac-client, Ruff). No prohibited tech introduced.
- [ ] **Spatial Integrity (IV)**: Any schema changes have a corresponding Alembic migration AND an `AGENTS.md` Section 4 update planned. SRID 4326 enforced. `confidence` CHECK constraint preserved.
- [ ] **API Resilience (V)**: All external API calls (Planetary Computer, iNaturalist, EDDMapS, USGS 3DEP) implement exponential backoff (3 retries), graceful skip on missing tiles, and `is_masked=TRUE` for `cloud_cover > 0.20`.
- [ ] **ML Registry (VI)**: Any model references use exact version strings from `AGENTS.md` Section 6. New versions registered in `AGENTS.md` before being referenced in code.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. The canonical Invasive Trace structure is shown — extend it;
  do NOT introduce top-level directories outside this layout without a constitution amendment.
-->

```text
app/
├── api/v1/           # FastAPI routers — one file per resource
├── models/           # SQLAlchemy ORM + GeoAlchemy2 table classes
├── services/         # Business logic: stac_client, indices, inat_consumer, eddmaps_consumer
├── ml/               # ML pipeline stages: stage1_anomaly, stage2_classifier, stage3_unet
└── scripts/          # One-off scripts: seed_observations, etc.

tests/
├── integration/      # DB + external API integration tests (use pytest-asyncio)
└── unit/             # Pure function unit tests (spectral indices, ML helpers)

migrations/           # Alembic migration scripts
models/               # Trained model artifact storage: models/{model_name}/{version}/
```

**Structure Decision**: [Document which app/ sub-packages this feature touches and any new files to be created]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
