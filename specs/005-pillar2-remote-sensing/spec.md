# Feature Specification: Pillar II - Remote Sensing Scene Ingestion

**Feature Branch**: `005-pillar2-remote-sensing`  
**Created**: 2026-03-30  
**Status**: Ready for Implementation  
**Input**: User description: "Create the missing feature specification artifact for the active feature in this repository."

## Problem Statement

Pillar II needs a production-aligned remote-sensing ingestion path that discovers Sentinel-2 scenes from Microsoft Planetary Computer, applies QA60 cloud-masking rules, computes canonical spectral indices, and persists ROI time-series data for downstream Stage 1 anomaly detection.

Without this feature, the project cannot generate reliable NDVI-based temporal sequences in `spectral_time_series`, and Stage 1 (`anomaly-v0.1.0`) remains blocked.

## Goals

- Deliver a deterministic ingestion workflow for ROI-scoped scene discovery and spectral metric persistence.
- Enforce AGENTS-defined external failure handling so ingestion degrades gracefully under partial outages.
- Guarantee idempotent writes for repeated ingestion of the same ROI/time window.
- Expose API endpoints that support both ingestion execution and retrieval of persisted spectral records.
- Preserve canonical schema semantics and nullability assumptions for `spectral_time_series`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest ROI Scene Time Series (Priority: P1)

As a contributor preparing Stage 1 anomaly input data, I need to ingest Planetary Computer scenes for an ROI and date range so NDVI/ENDVI/red-edge records are available in `spectral_time_series`.

**Why this priority**: Stage 1 depends on NDVI time series and cannot proceed without ingestion.

**Independent Test**: Can be fully tested by creating an ROI, invoking `POST /api/v1/scenes/ingest`, and verifying inserted/updated rows and ingestion summary counters.

**Acceptance Scenarios**:

1. **Given** a valid ROI and date range, **When** ingestion runs, **Then** STAC scenes are discovered from Planetary Computer and processed scene-by-scene.
2. **Given** an unmasked scene (`cloud_cover <= 0.20`), **When** processing completes, **Then** `ndvi`, `endvi`, and `red_edge` are persisted with `is_masked=FALSE`.
3. **Given** a masked scene (`cloud_cover > 0.20`), **When** processing completes, **Then** the scene is persisted with `is_masked=TRUE` and `ndvi=endvi=red_edge=NULL`.

---

### User Story 2 - Retrieve Spectral Records for Analysis (Priority: P2)

As a contributor validating temporal coverage, I need to query persisted scene records by ROI/date so I can inspect the time series before Stage 1 training/inference.

**Why this priority**: Retrieval is required to validate data quality and coverage but depends on ingestion existing first.

**Independent Test**: Can be fully tested by invoking `GET /api/v1/scenes` with and without filters and verifying ordering/filter semantics and masked-scene inclusion behavior.

**Acceptance Scenarios**:

1. **Given** persisted spectral rows, **When** `GET /api/v1/scenes` is called with `roi_id`, **Then** only records for that ROI are returned.
2. **Given** masked and unmasked rows exist, **When** `include_masked=false`, **Then** rows with `is_masked=TRUE` are excluded.
3. **Given** no matching records exist, **When** the endpoint is queried, **Then** the API returns `200` with an empty array.

---

### User Story 3 - Handle External and Data Failures Safely (Priority: P3)

As a maintainer, I need ingestion to survive rate limits and partial data failures so one bad scene or transient provider issue does not abort a full batch.

**Why this priority**: Reliability is required for operational use and contract compliance with AGENTS failure modes.

**Independent Test**: Can be fully tested by simulating HTTP 429 responses, missing assets, and complete STAC unavailability and verifying retry, skip/log, and terminal error semantics.

**Acceptance Scenarios**:

1. **Given** Planetary Computer returns HTTP 429, **When** retries are attempted, **Then** exponential backoff is applied with a maximum of 3 attempts and the endpoint follows this rule: return `200` when at least one usable scene is processed, otherwise return `500` when zero usable scenes remain.
2. **Given** a scene has missing/invalid assets, **When** it is processed, **Then** that scene is logged and skipped while the batch continues.
3. **Given** Planetary Computer is fully unavailable and no scenes can be retrieved after retries, **When** ingestion is requested, **Then** the API returns a terminal unavailability response (HTTP 500) with a clear error detail.

### Edge Cases

- ROI exists but STAC query returns 0 scenes for the requested date range.
- STAC returns partial results where some items are missing required spectral assets (`B03`, `B04`, `B05`, `B08`, `B8A`).
- QA60 asset is missing for a scene; the scene must be treated as fully clouded (`cloud_cover=1.0`, `is_masked=TRUE`).
- Cloud fraction equals threshold exactly (`cloud_cover == 0.20`); this is not masked because only values strictly greater than `0.20` are masked.
- Duplicate ingestion request repeats the same `(roi_id, stac_item)` set.
- ROI ID does not exist at ingestion time.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST discover scenes from Microsoft Planetary Computer STAC at `https://planetarycomputer.microsoft.com/api/stac/v1` for a supplied ROI and date range.
- **FR-002**: The system MUST sign STAC item assets through the Planetary Computer signing flow before raster access.
- **FR-003**: The system MUST compute scene-level cloud fraction from Sentinel-2 QA60 (bits 10 and 11) over the ROI window.
- **FR-004**: The system MUST set `is_masked=TRUE` when `cloud_cover > 0.20`; when masked, it MUST persist `ndvi=NULL`, `endvi=NULL`, and `red_edge=NULL`.
- **FR-005**: The system MUST compute NDVI, ENDVI, and red-edge metrics for unmasked scenes using the canonical Sentinel-2 band contract (NDVI: `B08/B04`, ENDVI: `B08/B03/B04`, red-edge: `B8A/B05`).
- **FR-006**: The system MUST persist processed scene outputs to `spectral_time_series` using canonical column names: `roi_id`, `scene_date`, `platform`, `stac_item`, `ndvi`, `endvi`, `red_edge`, `cloud_cover`, `is_masked`.
- **FR-007**: The system MUST implement idempotent persistence keyed by `(roi_id, stac_item)` using upsert behavior that inserts new rows and updates existing rows for repeated ingestion.
- **FR-008**: The system MUST expose `POST /api/v1/scenes/ingest` to execute ingestion and return a structured summary including queried, inserted, updated, masked, and skipped counts.
- **FR-009**: The system MUST expose `GET /api/v1/scenes` to list persisted records with ROI/date filters and optional masked-row inclusion.
- **FR-010**: For HTTP 429 from Planetary Computer, the system MUST apply exponential backoff with max 3 retries.
- **FR-011**: For missing tiles, partial STAC results, or per-scene read/asset failures, the system MUST log the issue and skip only the affected scene; it MUST NOT raise an unhandled exception that aborts the full batch. Missing QA60 is not a skip condition and MUST fall back to `cloud_cover=1.0` with `is_masked=TRUE`.
- **FR-012**: For terminal upstream unavailability (retries exhausted), `POST /api/v1/scenes/ingest` MUST return HTTP 500 only when zero usable scenes are available; if at least one usable scene is processed, it MUST return HTTP 200 with `scenes_skipped` reflecting failed scenes.
- **FR-013**: If `roi_id` is not found, `POST /api/v1/scenes/ingest` MUST return HTTP 404 and MUST NOT query STAC.
- **FR-014**: The ingestion output MUST preserve Stage 1 dependency semantics by ensuring unmasked rows provide ordered NDVI time-series values queryable by `roi_id` and `scene_date`.
- **FR-015**: For Wave 005, `platform` input support is limited to `sentinel-2`; `landsat-hls` and `naip` request values MUST return HTTP 422 until platform-specific ingestion rules are implemented.

### Non-Functional Constraints

- **NFR-001 (Latency)**: STAC discovery for a one-year window SHOULD complete within 15 seconds under expected batch sizes.
- **NFR-002 (Latency)**: End-to-end ingestion for up to 100 scenes SHOULD complete within 60 seconds under normal operating conditions.
- **NFR-003 (Latency)**: `GET /api/v1/scenes` SHOULD return within 2 seconds for an ROI with up to 365 stored records.
- **NFR-004 (Resilience)**: External failure handling MUST follow AGENTS API consumer policy (429 backoff max 3, partial skip-and-log behavior, no unhandled exceptions).
- **NFR-005 (Data Integrity)**: Schema usage MUST remain aligned with AGENTS Section 4 contracts; no column rename/type changes are permitted in this feature.

### Key Entities *(include if feature involves data)*

- **Spectral Time Series Record**: A row in `spectral_time_series` keyed operationally by `(roi_id, stac_item)` for idempotent ingestion; includes nullable `ndvi`, `endvi`, `red_edge`, nullable `cloud_cover`, and nullable `is_masked` (application logic always writes it).
- **Scene Ingestion Request**: API payload with `roi_id`, `start_date`, `end_date`, and `platform` used to initiate STAC discovery and processing.
- **Scene Ingestion Summary**: API response counts (`scenes_queried`, `scenes_inserted`, `scenes_updated`, `scenes_masked`, `scenes_skipped`) indicating ingestion outcome including partial success.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a valid ROI and date range, `POST /api/v1/scenes/ingest` returns `200` and persists at least one `spectral_time_series` row when at least one valid scene exists.
- **SC-002**: 100% of validated HTTP 429 scenarios either recover within 3 retries or are concluded with contract-compliant skip/terminal semantics without unhandled exceptions.
- **SC-003**: Re-running ingestion for the same ROI/date range does not create duplicate `(roi_id, stac_item)` rows.
- **SC-004**: For all rows with `cloud_cover > 0.20`, `is_masked=TRUE` and `ndvi/endvi/red_edge` are NULL.
- **SC-005**: Stage 1 downstream query (`roi_id`, ordered by `scene_date`) returns a usable NDVI time series from unmasked rows.
- **SC-006**: `GET /api/v1/scenes` supports ROI/date/masked filters and returns results in ascending `scene_date` order.
- **SC-007**: Under expected load targets, STAC discovery, ingestion batch runtime, and scene listing satisfy the defined latency constraints (15s, 60s, 2s respectively).

## Assumptions

- Wave 1 canonical tables already exist and include `spectral_time_series` as defined in AGENTS Section 4.
- The additive uniqueness constraint required for idempotent upsert (`(roi_id, stac_item)`) is applied via Wave 005 migration.
- Planetary Computer remains the production baseline remote-sensing source for this feature.
- This feature does not modify Stage 2 or Stage 3 model contracts.

## Out of Scope

- AlphaEarth or Earth Engine embedding ingestion and benchmark behavior.
- Stage 2 classifier training or Stage 3 U-Net hotspot inference.
- UI/dashboard workflows for human review.
- Changes to canonical schema column names, geometry types, or non-Wave-005 tables.
