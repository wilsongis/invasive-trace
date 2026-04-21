# Tasks: SGI Meeting Enhancement Suggestions

> **Executable Task List** — Wave 5 enhancement tasks derived from SGI team meeting.

---

## Wave 5.1: Canopy Height Integration

- [ ] **W5.1-T001:** Research Meta Canopy Height data format, access patterns, and licensing
- [ ] **W5.1-T002:** Identify tile coverage for SGI study areas
- [ ] **W5.1-T003:** Determine ingestion strategy (on-demand vs pre-cache)
- [ ] **W5.1-T004:** Create `app/services/canopy_height.py` — tile fetch, mosaic, zonal statistics
- [ ] **W5.1-T005:** Implement canopy height metric computation (mean, max, std, coverage %)
- [ ] **W5.1-T006:** Add retry-safe HTTP/GeoTIFF I/O with backoff
- [ ] **W5.1-T007:** Create Alembic migration for `canopy_height_metrics` table
- [ ] **W5.1-T008:** Create ORM model `app/models/canopy.py`
- [ ] **W5.1-T009:** Create Pydantic schemas `app/schemas/canopy.py`
- [ ] **W5.1-T010:** Implement `GET /api/v1/rois/{id}/canopy-metrics` endpoint
- [ ] **W5.1-T011:** Extend `app/services/feature_extractor.py` to include canopy height features
- [ ] **W5.1-T012:** Update Stage 2 training pipeline to accept canopy features
- [ ] **W5.1-T013:** Add canopy metrics to inference pipeline
- [ ] **W5.1-T014:** Unit tests for canopy height service
- [ ] **W5.1-T015:** Integration tests for canopy metrics endpoint
- [ ] **W5.1-T016:** End-to-end pipeline test with canopy features

---

## Wave 5.2: Woody Pressure Quantification

- [ ] **W5.2-T017:** Define Woody Pressure Index (WPI) formula with SGI ecologists
- [ ] **W5.2-T018:** Determine woody vs herbaceous spectral thresholds
- [ ] **W5.2-T019:** Validate WPI against known grassland degradation sites
- [ ] **W5.2-T020:** Create `app/services/woody_pressure.py` — WPI computation
- [ ] **W5.2-T021:** Implement multi-source WPI: canopy height + Sentinel-2 spectral + topography
- [ ] **W5.2-T022:** Add temporal WPI trend computation (if multi-temporal canopy available)
- [ ] **W5.2-T023:** Create Alembic migration: add `woody_pressure_score` to `invasion_predictions`
- [ ] **W5.2-T024:** Update ORM model `app/models/prediction.py`
- [ ] **W5.2-T025:** Update Pydantic schemas `app/schemas/prediction.py`
- [ ] **W5.2-T026:** Implement `GET /api/v1/rois/{id}/woody-pressure` endpoint
- [ ] **W5.2-T027:** Extend Stage 3 pipeline to compute dual scores (invasive + woody)
- [ ] **W5.2-T028:** Update `app/services/pipeline.py` orchestration
- [ ] **W5.2-T029:** Update `dashboard.html` to display dual scores
- [ ] **W5.2-T030:** Update `prediction_card.html` partial with woody pressure indicator
- [ ] **W5.2-T031:** Add WPI visualization (color-coded or progress bar)
- [ ] **W5.2-T032:** Unit tests for woody pressure service
- [ ] **W5.2-T033:** Integration tests for woody pressure endpoint
- [ ] **W5.2-T034:** Dashboard rendering tests

---

## Wave 5.3: Invasive Species Catalog

- [ ] **W5.3-T035:** Identify data sources (USDA PLANTS, EDDMapS state lists, extension services)
- [ ] **W5.3-T036:** Determine which states are in scope for SGI study areas
- [ ] **W5.3-T037:** Design species label normalization strategy
- [ ] **W5.3-T038:** Create `app/services/species_catalog.py` — catalog load, query, filter
- [ ] **W5.3-T039:** Implement state-based species filtering
- [ ] **W5.3-T040:** Add species deduplication and normalization
- [ ] **W5.3-T041:** Create Alembic migration for `invasive_species_catalog` table
- [ ] **W5.3-T042:** Create ORM model `app/models/species_catalog.py`
- [ ] **W5.3-T043:** Create Pydantic schemas `app/schemas/species.py`
- [ ] **W5.3-T044:** Implement `GET /api/v1/species?state=TX` endpoint
- [ ] **W5.3-T045:** Implement `POST /api/v1/species/sync` endpoint (admin)
- [ ] **W5.3-T046:** Extend Stage 2 `FeatureExtractor` to filter species by ROI state
- [ ] **W5.3-T047:** Add species catalog lookup to inference pipeline
- [ ] **W5.3-T048:** Unit tests for species catalog service
- [ ] **W5.3-T049:** Integration tests for species API endpoints
- [ ] **W5.3-T050:** Pipeline integration test with species filtering

---

## Wave 5.4: Pilot County Selection

- [ ] **W5.4-T051:** Download US Census TIGER/Line county boundaries
- [ ] **W5.4-T052:** Get SGI team's pilot county selections (state + county names or FIPS)
- [ ] **W5.4-T053:** Design pilot county activation workflow
- [ ] **W5.4-T054:** Create `app/services/pilot_county.py` — county load, query, activation
- [ ] **W5.4-T055:** Implement ROI-to-county spatial join
- [ ] **W5.4-T056:** Add pilot county filtering to prediction queries
- [ ] **W5.4-T057:** Create Alembic migration for `pilot_counties` table
- [ ] **W5.4-T058:** Create ORM model `app/models/pilot_county.py`
- [ ] **W5.4-T059:** Create Pydantic schemas `app/schemas/pilot_county.py`
- [ ] **W5.4-T060:** Implement `GET /api/v1/pilot-counties` endpoint
- [ ] **W5.4-T061:** Implement `POST /api/v1/pilot-counties` endpoint (admin)
- [ ] **W5.4-T062:** Add `pilot_county_id` FK to `regions_of_interest`
- [ ] **W5.4-T063:** Add pilot county filter to dashboard
- [ ] **W5.4-T064:** Add pilot county summary statistics
- [ ] **W5.4-T065:** Update prediction card to show pilot county context
- [ ] **W5.4-T066:** Unit tests for pilot county service
- [ ] **W5.4-T067:** Integration tests for pilot county endpoints
- [ ] **W5.4-T068:** Dashboard rendering tests with pilot county filter

---

## Summary

| Wave | Tasks | Status |
| :--- | :--- | :--- |
| 5.1 — Canopy Height | 16 tasks | Planned |
| 5.2 — Woody Pressure | 18 tasks | Planned (depends on 5.1) |
| 5.3 — Species Catalog | 16 tasks | Planned |
| 5.4 — Pilot Counties | 18 tasks | Planned |
| **Total** | **68 tasks** | |
