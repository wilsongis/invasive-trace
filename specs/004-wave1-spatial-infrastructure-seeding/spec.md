# Feature Specification: Wave 1 - Pillar I Spatial Infrastructure & Seeding

**Feature Branch**: `004-wave1-spatial-infrastructure-seeding`  
**Created**: 2026-03-27  
**Status**: Draft  
**Input**: User description: "Wave 1 — Pillar I: Spatial Infrastructure & Seeding. Depends on Wave 0 complete. Goal: four PostGIS tables created and queryable; ground-truth records seeded from iNaturalist and EDDMapS."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and Query Regions of Interest (Priority: P1)

As a contributor preparing the spatial foundation for the pipeline, I need the canonical PostGIS tables and ROI endpoints in place so study areas can be created, listed, and fetched through the production database path.

**Why this priority**: Wave 2 and all later ML work depend on `regions_of_interest` existing and being queryable. Without the schema and ROI API, no downstream spatial processing can begin safely.

**Independent Test**: Can be fully tested by applying the Wave 1 migration, creating an ROI through `POST /api/v1/rois`, and confirming that `GET /api/v1/rois` and `GET /api/v1/rois/{id}` return persisted geometry in GeoJSON form.

**Acceptance Scenarios**:

1. **Given** the Wave 1 migration has been applied, **When** a contributor creates an ROI with WKT polygon input, **Then** the system stores it in `regions_of_interest` as `GEOMETRY(POLYGON, 4326)` with the canonical schema.
2. **Given** one or more ROIs exist, **When** the contributor requests the ROI list, **Then** the system returns the persisted study areas without exposing non-canonical geometry formats.
3. **Given** an ROI exists, **When** the contributor requests `GET /api/v1/rois/{id}`, **Then** the response includes the ROI geometry serialized as GeoJSON.

---

### User Story 2 - Seed Ground-Truth Observations (Priority: P2)

As a contributor preparing the supervised data layer, I need iNaturalist and EDDMapS records ingested into `ground_truth_observations` so later classifier training and validation can start from a reproducible source of labeled occurrences.

**Why this priority**: The Stage 2 classifier and benchmark work require labeled ground truth. Observation ingestion is valuable once ROI storage is working, but it is secondary to establishing the spatial schema itself.

**Independent Test**: Can be fully tested by running the seed workflow for a configurable taxon list and bounding box, then confirming the database receives at least one stored observation row with canonical fields and raw payload persistence.

**Acceptance Scenarios**:

1. **Given** valid API credentials and a target extent are configured, **When** the seed workflow calls iNaturalist and EDDMapS, **Then** successful responses are written into `ground_truth_observations` with source-specific metadata preserved in `raw_payload`.
2. **Given** an external source returns HTTP 429, **When** the consumer retries up to three times, **Then** the request eventually succeeds or is logged and skipped without crashing the workflow.
3. **Given** one source fails while the other succeeds, **When** the seed run completes, **Then** the system returns a partial-success summary rather than aborting the entire sync.

---

### User Story 3 - Run ROI-Scoped Observation Sync (Priority: P3)

As a contributor validating the Wave 1 API surface, I need an ROI-scoped sync endpoint that triggers observation ingestion and returns a summary payload so spatial setup and seeding can be exercised through the app, not only through a script.

**Why this priority**: This provides the bridge from foundational data plumbing to application-facing workflow, but it should only be built after the canonical tables and core consumers exist.

**Independent Test**: Can be fully tested by creating an ROI, invoking `POST /api/v1/observations/sync` with that ROI, and confirming the response reports `sources_polled`, `records_inserted`, and `records_skipped` while persisting successful records.

**Acceptance Scenarios**:

1. **Given** an ROI exists, **When** the contributor invokes the observation sync endpoint for that ROI, **Then** the system uses the ROI geometry to bound source queries and returns a structured summary payload.
2. **Given** one source encounters rate limiting or another recoverable failure, **When** the sync endpoint completes, **Then** the response reports skipped records while preserving successful inserts.
3. **Given** the sync endpoint completes successfully, **When** the contributor inspects the database, **Then** new `ground_truth_observations` rows exist for the synced ROI extent.

### Edge Cases

- An ROI WKT payload is invalid, non-polygonal, or cannot be converted into SRID 4326 geometry.
- A migration is generated but omits one or more required CHECK constraints, FK constraints, or GiST indexes from the canonical DDL.
- `POST /api/v1/rois` receives valid text fields but malformed geometry and must reject the request without partially writing data.
- iNaturalist or EDDMapS returns HTTP 429 for all three retry attempts, requiring a logged skip instead of an unhandled exception.
- iNaturalist or EDDMapS returns incomplete or malformed payload data for one record while other records remain usable.
- A sync request targets an ROI that does not exist and must return a clear application error.
- Duplicate observation records from repeated source syncs must be handled deterministically rather than silently corrupting the stored dataset.
- Wave 2 remote-sensing tasks are referenced during Wave 1 implementation even though STAC querying and spectral ingestion are not part of this feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Wave 1 MUST create ORM models for `regions_of_interest`, `invasion_predictions`, `ground_truth_observations`, and `spectral_time_series` that match `AGENTS.md` Section 4 exactly, including geometry types, SRID 4326, CHECK constraints, foreign keys, and index expectations.
- **FR-002**: Wave 1 MUST generate and apply an Alembic migration that creates all four canonical PostGIS tables with GiST indexes on geometry columns and all documented CHECK constraints.
- **FR-003**: The system MUST provide ROI API endpoints at `POST /api/v1/rois`, `GET /api/v1/rois/{id}`, and `GET /api/v1/rois`.
- **FR-004**: The ROI create flow MUST accept WKT polygon input and return persisted geometry as GeoJSON in API responses.
- **FR-005**: The system MUST reject invalid ROI geometry inputs without partially writing database state.
- **FR-006**: The iNaturalist consumer MUST call `https://api.inaturalist.org/v1/observations` using async HTTP requests, retry HTTP 429 responses with exponential backoff up to 3 times, and log-and-skip unrecoverable failures.
- **FR-007**: The EDDMapS consumer MUST implement the same resilience contract as the iNaturalist consumer and persist successful records into `ground_truth_observations`.
- **FR-008**: Successful observation ingestion MUST preserve source provenance, external IDs when present, canonical geometry, and the full upstream payload in `raw_payload`.
- **FR-009**: The repository MUST provide a CLI seeding entry point that calls both observation consumers for a configurable taxon list and bounding box and is invokable through `just seed-data`.
- **FR-010**: The system MUST provide `POST /api/v1/observations/sync` to trigger ROI-scoped iNaturalist and EDDMapS ingestion and return a summary containing `sources_polled`, `records_inserted`, and `records_skipped`.
- **FR-011**: The observation sync endpoint MUST return HTTP 404 when the requested ROI does not exist, with a JSON error payload that includes a stable `code` value of `ROI_NOT_FOUND` and a human-readable `message`.
- **FR-012**: Wave 1 MUST remain scoped to spatial infrastructure and seeding; Planetary Computer STAC querying, spectral index computation, and scene ingestion belong to Wave 2 and MUST NOT be implemented as part of this feature.
- **FR-013**: The canonical schema introduced in Wave 1 MUST preserve the nullable tri-state semantics of `invasion_predictions.validated` and the Stage 2 lineage rule for `invasion_predictions.model_version` defined in `AGENTS.md`.
- **FR-014**: Wave 1 completion MUST require `just db-migrate` to create the four canonical tables, `just seed-data` to insert at least one observation row, and `POST /api/v1/rois` to return HTTP 201 with GeoJSON geometry.
- **FR-015**: Wave 1 observation ingestion MUST apply a single deterministic duplicate-handling strategy: skip-on-conflict with a unique key on (`source`, `external_id`) when `external_id` is present, and log-and-skip records missing `external_id` to avoid ambiguous duplicate writes.
- **FR-016**: The CLI seeding entry point MUST support a dry-run mode that performs source fetch and summary accounting but does not write any rows to `ground_truth_observations`.

### Key Entities *(include if feature involves data)*

- **Region of Interest**: Canonical `regions_of_interest` row with UUID identity, WGS84 polygon geometry, descriptive metadata, and GiST-indexed spatial lookup.
- **Invasion Prediction**: Canonical `invasion_predictions` row introduced by the migration for downstream pipeline use, including Stage 2 lineage and tri-state validation semantics.
- **Ground-Truth Observation**: Canonical `ground_truth_observations` row populated from iNaturalist, EDDMapS, or field survey data, preserving source provenance and raw payload.
- **Spectral Time Series Record**: Canonical `spectral_time_series` row introduced by the migration for later Wave 2 scene ingestion.
- **ROI Sync Summary**: API response payload reporting which sources were polled and how many records were inserted or skipped during ROI-scoped observation ingestion.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `just db-migrate` creates all four canonical tables with the expected geometry types, indexes, and CHECK constraints in one successful run against the local PostGIS environment.
- **SC-002**: `POST /api/v1/rois` returns HTTP 201 and GeoJSON geometry for valid WKT polygon input, and `GET /api/v1/rois/{id}` returns the same persisted geometry.
- **SC-003**: `just seed-data` inserts at least one `ground_truth_observations` row during a validated local run with available source credentials.
- **SC-004**: 100% of HTTP 429 responses encountered during Wave 1 validation runs are either recovered within 3 retries or logged as skipped without crashing the process.
- **SC-005**: `POST /api/v1/observations/sync` returns a summary payload containing `sources_polled`, `records_inserted`, and `records_skipped` for every completed ROI-scoped sync request.
- **SC-006**: Wave 1 leaves the repository ready for Wave 2 by making `regions_of_interest` queryable through the API and `spectral_time_series` available in the canonical schema without implementing STAC ingestion yet.
- **SC-007**: Dry-run seeding mode reports `sources_polled`, `records_inserted`, and `records_skipped` while producing zero new rows in `ground_truth_observations` for the dry-run execution.

## Assumptions

- Wave 0 bootstrap work is complete and the repository can already start, migrate, lint, and test successfully.
- Valid iNaturalist and EDDMapS credentials are available through environment variables when source-backed validation is performed.
- Source APIs provide enough location and metadata fields to map successful records into `ground_truth_observations` without requiring canonical schema changes.
- Duplicate-observation handling can be implemented within the Wave 1 seeding logic without introducing non-canonical tables.
- Wave 2 remote-sensing work will be specified separately even though this feature prepares the schema it depends on.

## Out of Scope

- Planetary Computer STAC querying, Sentinel-2 scene discovery, or cloud-masked scene ingestion.
- NDVI, ENDVI, or red-edge computation logic.
- Pipeline inference, classifier training, hotspot scoring, or HITL validation workflows.
- Any change to the contract-locked column names or geometry types beyond implementing the canonical Wave 1 migration.
