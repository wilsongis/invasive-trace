# Project Goals — Invasive Trace

*This file is read by `/warden.audit` to cross-reference proposed features against project intent.*

## Primary Objective
- Build a geospatial AI platform that detects and maps invasive plant species across Southern Grassland Institute study areas using multi-temporal satellite imagery, spectral phenology analysis, and a three-stage ML execution chain.

## Non-Goals (Explicit Exclusions)
- Do NOT build general-purpose user authentication (JWT/OAuth out of scope for MVP; role gate is HITL reviewer only).
- Do NOT add client-side analytics or third-party telemetry.
- Do NOT support raster formats other than COG (Cloud-Optimized GeoTIFF) for storage.
- Do NOT build a mobile-first UI (desktop expert-review dashboard only for MVP).

## Success Criteria
- [ ] `just verify` passes with zero errors.
- [ ] All four PostGIS tables created via Alembic migrations (`just db-migrate`).
- [x] `POST /api/v1/observations/sync` successfully seeds ≥ 1 iNaturalist record into `ground_truth_observations`.
- [x] Sentinel-2 STAC query returns a valid scene for a test ROI geometry.
- [x] Stage 1 anomaly detector produces a non-empty NDVI departure list on synthetic time series.
- [ ] HITL dashboard renders predictions on a Leaflet map and accepts confirm/reject actions.
- [ ] Retraining trigger fires when confirmed + rejected predictions batch reaches 50.

## Out of Scope (MVP)
- EDDMapS write-back / field survey mobile collection
- Real-time streaming inference
- Multi-tenant / organisation-level data isolation
