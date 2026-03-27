# Invasive Trace

Geospatial AI platform for the **Southern Grassland Institute** — detects, classifies, and maps invasive plant species across study areas using multi-temporal satellite imagery, spectral phenology analysis, and a three-stage ML execution chain.

## Overview

| Component | Technology |
|:---|:---|
| **Backend** | FastAPI + Python 3.12 (`uv`) |
| **Database** | PostgreSQL 16 + PostGIS 3.4 |
| **ORM / Spatial** | SQLAlchemy (async) + GeoAlchemy2 |
| **Frontend** | Jinja2 + HTMX + Tailwind CSS |
| **Raster I/O** | Rasterio + GDAL (COG-native) |
| **Remote Sensing** | pystac-client + planetary-computer (Sentinel-2 L2A) |
| **ML: Classical** | Scikit-learn · XGBoost (spectral feature vectors) |
| **ML: Deep** | PyTorch U-Net (spatial texture / hotspot scoring) |
| **Container** | Podman + Containerfile |
| **Automation** | `just` |

## Quick Start

**Prerequisites:** Podman, `just`, `uv`

```bash
# 1. Copy environment variables and supply API keys
cp .env.example .env

# 2. Start PostGIS + FastAPI via Podman compose
just start

# 3. Apply database migrations
just db-migrate

# 4. Seed ground-truth observations (iNaturalist + EDDMapS)
just seed-data
```

The API will be available at `http://localhost:8000`.

## AI Execution Chain

Three-stage pipeline that runs against every Region of Interest (ROI):

| Stage | Model | Purpose |
|:---|:---|:---|
| **Stage 1** | `AnomalyDetector` (IsolationForest / Z-score) | Detect temporal NDVI departures (invasive early green-up) |
| **Stage 2** | `FocalClassifier` (RandomForest / XGBoost) | Species-level spectral discrimination + confidence score |
| **Stage 3** | `UNetTexture` (PyTorch U-Net, 512×512 patches) | Spatial texture analysis → hotspot spread-risk score |

## Command Reference

| Command | Description |
|:---|:---|
| `just start` | Build if needed; start full Podman compose stack (app + PostGIS) |
| `just stop` | Stop and remove all compose containers |
| `just run` | Run FastAPI natively via `uv` (requires local PostGIS) |
| `just db-migrate` | Apply Alembic migrations |
| `just db-rollback` | Roll back the last migration |
| `just db-revision msg="…"` | Autogenerate a new migration from model changes |
| `just seed-data` | Fetch iNaturalist + EDDMapS records into `ground_truth_observations` |
| `just research-sync` | Push `/docs/research` to NotebookLM |
| `just lint` | Ruff check + format |
| `just test` | Run pytest suite |
| `just verify` | lint + test |

## Data Sources

- **Microsoft Planetary Computer** — Sentinel-2 L2A, Landsat HLS, NAIP (STAC v1)
- **iNaturalist API** — Taxon-filtered invasive species observations (`INAT_API_KEY`)
- **EDDMapS API** — Regional occurrence records (`EDDMAPS_API_KEY`)
- **USGS 3DEP** — Elevation context for topographic modelling (public, no key required)

All external consumers implement exponential backoff (3 retries) on HTTP 429 and skip cloud-masked scenes (`cloud_cover > 0.20`).

## Database Schema

Four PostGIS tables with GiST spatial indexes — see [`AGENTS.md`](AGENTS.md#4-postgis-schema-canonical) for the canonical DDL and [`docs/research/03-DATA-DICTIONARY.md`](docs/research/03-DATA-DICTIONARY.md) for the full column dictionary.

- `regions_of_interest` — WGS84 study-area polygons
- `spectral_time_series` — Per-scene NDVI / ENDVI / Red-Edge indices
- `invasion_predictions` — Model outputs with confidence + hotspot score
- `ground_truth_observations` — iNaturalist / EDDMapS / field-survey records

## AI Agent Onboarding

This project follows the **Read-Execute-Write Memory Protocol**. All agents must:

1. **READ** [`AGENTS.md`](AGENTS.md) before every task — schema, API contracts, and ML registry are defined there.
2. **EXECUTE** using the standard stack only (see `STACK.md`).
3. **WRITE** an update to `AGENTS.md` after every architectural decision.

> "Take a deep breath and work on this problem step by step."