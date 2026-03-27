# System Architecture — Invasive Trace

## 1. High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  External Data Sources                                              │
│  ┌──────────────────┐  ┌───────────────┐  ┌──────────────────┐     │
│  │ Planetary Computer│  │  iNaturalist  │  │    EDDMapS       │     │
│  │  (STAC / COG)    │  │  API v1       │  │    API           │     │
│  └────────┬─────────┘  └──────┬────────┘  └────────┬─────────┘     │
└───────────┼────────────────────┼────────────────────┼───────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FastAPI Application (Python 3.12)                                  │
│  app/                                                               │
│  ├── api/          REST endpoints (versioned: /api/v1/)             │
│  ├── models/       SQLAlchemy ORM + GeoAlchemy2                     │
│  ├── services/                                                      │
│  │   ├── stac_client.py    Planetary Computer queries                │
│  │   ├── indices.py        NDVI / ENDVI / Red-Edge                  │
│  │   ├── inat_consumer.py  iNaturalist seeder                       │
│  │   └── eddmaps_consumer.py                                        │
│  └── ml/                                                            │
│      ├── stage1_anomaly.py  IsolationForest / Z-score               │
│      ├── stage2_classifier.py  RandomForest / XGBoost               │
│      └── stage3_unet.py    PyTorch U-Net inference                  │
└───────────────────────────┬─────────────────────────────────────────┘
                             │  asyncpg / SQLAlchemy async
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PostgreSQL 16 + PostGIS 3.4                                        │
│  regions_of_interest  │  invasion_predictions                       │
│  spectral_time_series │  ground_truth_observations                  │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. Global Tech Stack
See `AGENTS.md` Section 3 for the full table. No deviation permitted.

## 3. Data Flow — Remote Sensing Pipeline
1. Analyst defines ROI polygon → stored in `regions_of_interest`.
2. STAC client queries Planetary Computer for all Sentinel-2 L2A scenes intersecting ROI within date range.
3. Cloud-mask filter applied (QA60): scenes with `cloud_cover > 0.20` marked `is_masked=TRUE`.
4. For accepted scenes: NDVI computed from B08/B04, ENDVI from B08/B04/B03, and the red-edge metric from the Sentinel-2 red-edge bands (B05/B8A, formula-specific); results stored in `spectral_time_series`.
5. Stage 1 anomaly detector compares scene NDVI against seasonal baseline; flags anomalous pixels.
6. Stage 2 classifier assigns species label + confidence per flagged cluster.
7. Stage 3 U-Net scores spatial hotspot risk for each prediction.
8. Predictions written to `invasion_predictions`.
9. HITL reviewer validates via Leaflet dashboard → `validated` transitions from `NULL` to `TRUE` (confirmed) or `FALSE` (rejected).
10. At batch ≥ 50 reviewed records (`validated IS NOT NULL`): retraining job triggered.

## 4. API Versioning
All REST endpoints live under `/api/v1/`. Breaking changes require a new version prefix.
