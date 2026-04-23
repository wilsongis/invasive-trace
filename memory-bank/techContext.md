# Tech Context: Invasive Trace

## Technology Stack

| Layer | Technology | Version / Constraint |
| :--- | :--- | :--- |
| **Backend** | FastAPI | Python 3.12; no Django/Flask |
| **Database** | PostgreSQL + PostGIS | 16 + 3.4; no SQLite/MongoDB |
| **ORM / Spatial** | SQLAlchemy (async) + GeoAlchemy2 | Strictly typed geometries |
| **Frontend** | Jinja2 + HTMX + Tailwind CSS | No React/Vue/Svelte |
| **Raster I/O** | Rasterio + GDAL | COG-native reads only; via Containerfile |
| **Remote Sensing** | pystac-client + planetary-computer | Production baseline; Planetary Computer STAC v1 |
| **ML Benchmark** | Google Earth Engine / AlphaEarth | Benchmark-only; `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` |
| **ML: Classical** | Scikit-learn | RandomForest / XGBoost; spectral feature vectors |
| **ML: Deep** | PyTorch | U-Net architecture; 512×512 patches |
| **Package Manager** | `uv` | Strictly; no pip/poetry |
| **Container** | Podman + Containerfile | No Docker Desktop |
| **Automation** | `just` | No Makefile |
| **Migrations** | Alembic | Async env wired to `DATABASE_URL` |
| **Linting** | Ruff | No flake8/black/pylint |
| **Settings** | pydantic-settings | `app/config.py` |

## Development Setup

### Prerequisites
- Podman (container runtime)
- `just` (task runner)
- `uv` (Python package manager)
- Python 3.12

### Environment Variables
| Variable | Purpose |
| :--- | :--- |
| `DATABASE_URL` | Async PostgreSQL connection string |
| `INAT_API_KEY` | iNaturalist API key |
| `EDDMAPS_API_KEY` | EDDMapS API key |
| `EE_PROJECT_ID` | Google Earth Engine project (benchmark-only; optional) |

### Key Commands
| Command | Action |
| :--- | :--- |
| `just start` | Build + start Podman compose stack (app + PostGIS) |
| `just run` | Native FastAPI start via `uv` (rapid iteration) |
| `just db-migrate` | Apply Alembic migrations |
| `just seed-data` | Fetch iNaturalist + EDDMapS into `ground_truth_observations` |
| `just verify` | **Quality gate**: ruff + pytest (must pass before pillar complete) |
| `just lint` | Ruff check + format |
| `just test` | Pytest via uv |
| `just research-sync` | Connect MCP to gaia-atlas NotebookLM notebook |
| `just research-test` | Verify MCP connection |

## Project Structure
```
app/
  config.py          # pydantic-settings runtime config
  db.py              # async SQLAlchemy engine + get_db dependency
  main.py            # FastAPI app, lifespan, routers
  api/v1/            # REST endpoints (rois, scenes, predictions, observations, dashboard)
  ml/                # Stage 1/2/3 model implementations
  models/            # SQLAlchemy ORM models
  schemas/           # Pydantic request/response schemas
  scripts/           # CLI entrypoints (invoked by justfile)
  services/          # Business logic (stac_client, scene_ingestion, consumers, etc.)
  templates/         # Jinja2 HTML templates + HTMX partials
migrations/
  versions/          # Alembic migration chain (0001→0004)
models/              # Trained model artifacts (FocalClassifier/rf-v0.1.0/)
specs/               # Spec-driven development artifacts (spec/plan/tasks per feature)
tests/
  unit/              # Pure unit tests (no DB)
  integration/       # DB/API integration tests (require PostGIS container)
docs/research/       # NotebookLM source documents
```

## External API Contracts
| Service | Endpoint | Auth |
| :--- | :--- | :--- |
| Planetary Computer STAC | `https://planetarycomputer.microsoft.com/api/stac/v1` | planetary-computer token lib |
| iNaturalist | `https://api.inaturalist.org/v1/observations` | `INAT_API_KEY` |
| EDDMapS | `https://www.eddmaps.org/api/` | `EDDMAPS_API_KEY` |
| USGS 3DEP | `https://tnmapi.cr.usgs.gov/api/` | None (public) |
| Google Earth Engine | `https://earthengine.googleapis.com/` | GCloud auth (benchmark-only) |

## Sentinel-2 Band Contract
- **NDVI:** B08 (NIR) + B04 (Red)
- **ENDVI:** B08 (NIR) + B04 (Red) + B03 (Green)
- **Red-edge:** B05/B8A (Red-Edge Chlorophyll Index)
- **Cloud mask:** QA60 band; `cloud_cover > 0.20` → `is_masked=TRUE`

## Technical Constraints
- All geometries in WGS84 (EPSG:4326)
- `invasion_predictions.geom` is `GEOMETRY(POINT, 4326)` — never null (centroid fallback)
- `regions_of_interest.geom` is `GEOMETRY(POLYGON, 4326)`
- COG-native raster reads only (no local raster file writes in production)
- AlphaEarth embeddings must NOT be used in production Stage 1 or 2 pipelines
- DB integration tests require a running PostGIS container; excluded from CI unit-only runs