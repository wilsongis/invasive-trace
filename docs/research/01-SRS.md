# Software Requirements Specification (SRS) — Invasive Trace

## 1. Introduction
**Purpose:** Define the functional and non-functional requirements for Invasive Trace, a geospatial AI platform for the Southern Grassland Institute to detect, classify, and map invasive plant species.
**Scope:** Multi-temporal remote sensing ingestion, spectral anomaly detection, species classification, hotspot scoring, and Human-in-the-Loop (HITL) validation.
**Definitions:**
- **ROI** — Region of Interest (PostGIS polygon, SRID 4326)
- **NDVI** — Normalized Difference Vegetation Index
- **ENDVI** — Enhanced NDVI (red-edge formulation)
- **COG** — Cloud-Optimized GeoTIFF (native raster format)
- **STAC** — SpatioTemporal Asset Catalog (Planetary Computer)
- **HITL** — Human-in-the-Loop (expert validation workflow)

## 2. Overall Description
- **Users:** Remote sensing analysts, ecologists, HITL reviewers at the Southern Grassland Institute.
- **Key dependencies:** Microsoft Planetary Computer (Sentinel-2 L2A), iNaturalist API, EDDMapS API, USGS 3DEP.
- **Operating environment:** Podman-containerized PostGIS + FastAPI, macOS/Linux.

## 3. Functional Requirements

| ID | Requirement |
|:---|:---|
| FR-01 | System SHALL store ROI polygons in `regions_of_interest` with GiST spatial index. |
| FR-02 | System SHALL query Planetary Computer STAC for Sentinel-2 L2A scenes intersecting an ROI. |
| FR-03 | System SHALL calculate NDVI, ENDVI, and Red-Edge indices per scene and store in `spectral_time_series`, using Sentinel-2 B08/B04 for NDVI, B08/B04/B03 for ENDVI, and the red-edge bands for the red-edge metric. |
| FR-04 | System SHALL flag scenes with `cloud_cover > 0.20` as `is_masked=TRUE`. |
| FR-05 | System SHALL seed `ground_truth_observations` from iNaturalist and EDDMapS APIs. |
| FR-06 | Stage 1 anomaly detector SHALL flag temporal NDVI departures (invasive early green-up). |
| FR-07 | Stage 2 classifier SHALL output species label + confidence for flagged pixels. |
| FR-08 | Stage 3 U-Net SHALL produce a `hotspot_score` (0–1) for spatial spread risk. |
| FR-09 | HITL dashboard SHALL display predictions on a Leaflet map and accept confirm/reject, with `validated` stored as `NULL` (pending), `TRUE` (confirmed), or `FALSE` (rejected). |
| FR-10 | Confirmed/rejected batches ≥ 50 SHALL trigger model retraining; unreviewed predictions (`validated IS NULL`) SHALL NOT count toward the batch threshold. |

## 4. Non-Functional Requirements
- **Resilience:** All external API consumers MUST implement exponential backoff (3 retries) on HTTP 429.
- **Interoperability:** All raster outputs MUST be COG-compatible; all catalog queries MUST be STAC v1.
- **Data integrity:** `confidence` column constrained `BETWEEN 0.0 AND 1.0` at the DB layer.
- **Review integrity:** new predictions remain unreviewed until a human acts; `validated` must remain nullable to distinguish pending from rejected.
- **Security:** API keys stored in environment variables only; never logged or serialised.

## 5. Verification Methods
- `just verify` — Ruff lint + pytest suite must pass with zero errors.
- Integration test: STAC query for a test ROI returns ≥ 1 scene.
- Unit test: NDVI calculation correct for synthetic band arrays.
