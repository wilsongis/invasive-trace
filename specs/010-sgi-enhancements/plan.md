# Plan: SGI Meeting Enhancement Suggestions

> **Implementation Plan** — Wave 5 enhancement roadmap based on SGI team meeting outcomes.

---

## 1. Overview

This plan covers four new waves (5.1–5.4) derived from the SGI team meeting on 2026-04-21. Suggestion 1 (EDDMapS/iNaturalist ground truth) is already implemented and requires no work.

---

## 2. Wave 5.1: Canopy Height Integration (Suggestion 2)

### Phase 0: Research & Data Acquisition
- **T001:** Research Meta Canopy Height data format, access patterns, and licensing
- **T002:** Identify tile coverage for SGI study areas
- **T003:** Determine ingestion strategy (on-demand vs pre-cache)

### Phase 1: Service Implementation
- **T004:** Create `app/services/canopy_height.py` — tile fetch, mosaic, zonal statistics
- **T005:** Implement canopy height metric computation (mean, max, std, coverage %)
- **T006:** Add retry-safe HTTP/GeoTIFF I/O with backoff

### Phase 2: Schema & API
- **T007:** Create Alembic migration for `canopy_height_metrics` table
- **T008:** Create ORM model `app/models/canopy.py`
- **T009:** Create Pydantic schemas `app/schemas/canopy.py`
- **T010:** Implement `GET /api/v1/rois/{id}/canopy-metrics` endpoint

### Phase 3: Pipeline Integration
- **T011:** Extend `app/services/feature_extractor.py` to include canopy height features
- **T012:** Update Stage 2 training pipeline to accept canopy features
- **T013:** Add canopy metrics to inference pipeline

### Phase 4: Testing
- **T014:** Unit tests for canopy height service
- **T015:** Integration tests for canopy metrics endpoint
- **T016:** End-to-end pipeline test with canopy features

---

## 3. Wave 5.2: Woody Pressure Quantification (Suggestions 3 & 4)

### Phase 0: Research & Formula Design
- **T017:** Define Woody Pressure Index (WPI) formula with SGI ecologists
- **T018:** Determine woody vs herbaceous spectral thresholds
- **T019:** Validate WPI against known grassland degradation sites

### Phase 1: Service Implementation
- **T020:** Create `app/services/woody_pressure.py` — WPI computation
- **T021:** Implement multi-source WPI: canopy height + Sentinel-2 spectral + topography
- **T022:** Add temporal WPI trend computation (if multi-temporal canopy available)

### Phase 2: Schema & API
- **T023:** Create Alembic migration: add `woody_pressure_score` to `invasion_predictions`
- **T024:** Update ORM model `app/models/prediction.py`
- **T025:** Update Pydantic schemas `app/schemas/prediction.py`
- **T026:** Implement `GET /api/v1/rois/{id}/woody-pressure` endpoint

### Phase 3: Pipeline Integration
- **T027:** Extend Stage 3 pipeline to compute dual scores (invasive + woody)
- **T028:** Update `app/services/pipeline.py` orchestration

### Phase 4: Dashboard Updates
- **T029:** Update `dashboard.html` to display dual scores
- **T030:** Update `prediction_card.html` partial with woody pressure indicator
- **T031:** Add WPI visualization (color-coded or progress bar)

### Phase 5: Testing
- **T032:** Unit tests for woody pressure service
- **T033:** Integration tests for woody pressure endpoint
- **T034:** Dashboard rendering tests

---

## 4. Wave 5.3: Invasive Species Catalog (Suggestion 5)

### Phase 0: Research & Data Acquisition
- **T035:** Identify data sources (USDA PLANTS, EDDMapS state lists, extension services)
- **T036:** Determine which states are in scope for SGI study areas
- **T037:** Design species label normalization strategy

### Phase 1: Service Implementation
- **T038:** Create `app/services/species_catalog.py` — catalog load, query, filter
- **T039:** Implement state-based species filtering
- **T040:** Add species deduplication and normalization

### Phase 2: Schema & API
- **T041:** Create Alembic migration for `invasive_species_catalog` table
- **T042:** Create ORM model `app/models/species_catalog.py`
- **T043:** Create Pydantic schemas `app/schemas/species.py`
- **T044:** Implement `GET /api/v1/species?state=TX` endpoint
- **T045:** Implement `POST /api/v1/species/sync` endpoint (admin)

### Phase 3: Pipeline Integration
- **T046:** Extend Stage 2 `FeatureExtractor` to filter species by ROI state
- **T047:** Add species catalog lookup to inference pipeline

### Phase 4: Testing
- **T048:** Unit tests for species catalog service
- **T049:** Integration tests for species API endpoints
- **T050:** Pipeline integration test with species filtering

---

## 5. Wave 5.4: Pilot County Selection (Suggestion 6)

### Phase 0: Research & Data Acquisition
- **T051:** Download US Census TIGER/Line county boundaries
- **T052:** Get SGI team's pilot county selections (state + county names or FIPS)
- **T053:** Design pilot county activation workflow

### Phase 1: Service Implementation
- **T054:** Create `app/services/pilot_county.py` — county load, query, activation
- **T055:** Implement ROI-to-county spatial join
- **T056:** Add pilot county filtering to prediction queries

### Phase 2: Schema & API
- **T057:** Create Alembic migration for `pilot_counties` table
- **T058:** Create ORM model `app/models/pilot_county.py`
- **T059:** Create Pydantic schemas `app/schemas/pilot_county.py`
- **T060:** Implement `GET /api/v1/pilot-counties` endpoint
- **T061:** Implement `POST /api/v1/pilot-counties` endpoint (admin)
- **T062:** Add `pilot_county_id` FK to `regions_of_interest`

### Phase 3: Dashboard Updates
- **T063:** Add pilot county filter to dashboard
- **T064:** Add pilot county summary statistics
- **T065:** Update prediction card to show pilot county context

### Phase 4: Testing
- **T066:** Unit tests for pilot county service
- **T067:** Integration tests for pilot county endpoints
- **T068:** Dashboard rendering tests with pilot county filter

---

## 6. Dependencies Graph

```
Wave 5.1 (Canopy Height)
    └── Wave 5.2 (Woody Pressure) [depends on canopy height data]

Wave 5.3 (Species Catalog) [independent]

Wave 5.4 (Pilot Counties) [independent]
```

---

## 7. Quality Gates

Each wave must pass:
- `just lint` — 0 ruff errors
- `just test` — 0 test failures
- Schema migration applies cleanly
- API contract documented in `AGENTS.md`
