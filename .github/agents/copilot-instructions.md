# invasive-trace Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-07

## Active Technologies
- Python 3.12 (managed by `uv`) + FastAPI, SQLAlchemy (async) + GeoAlchemy2, Rasterio, pystac-client, planetary-computer, scikit-learn, joblib, numpy, PyTorch (U-Net) (009-stage2-focal-classifier)
- PostgreSQL 16 + PostGIS 3.4 — four canonical tables: `regions_of_interest`, `invasion_predictions`, `ground_truth_observations`, `spectral_time_series` (009-stage2-focal-classifier)
- Python 3.12 (managed by `uv`) + FastAPI, SQLAlchemy (async) + GeoAlchemy2, scikit-learn (RandomForest/XGBoost), Rasterio, pystac-client, planetary-computer (009-stage2-focal-classifier)
- PostgreSQL 16 + PostGIS 3.4 — reads from `ground_truth_observations`, `spectral_time_series`, `regions_of_interest`; writes to `invasion_predictions` (009-stage2-focal-classifier)

- Python 3.12 (managed by `uv`) + FastAPI, SQLAlchemy (async) + GeoAlchemy2, scikit-learn, PyTorch, joblib, httpx, Pydantic, numpy (007-wave3-ai-chain)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12 (managed by `uv`): Follow standard conventions

## Recent Changes
- 009-stage2-focal-classifier: Added Python 3.12 (managed by `uv`) + FastAPI, SQLAlchemy (async) + GeoAlchemy2, scikit-learn (RandomForest/XGBoost), Rasterio, pystac-client, planetary-computer
- 009-stage2-focal-classifier: Added Python 3.12 (managed by `uv`) + FastAPI, SQLAlchemy (async) + GeoAlchemy2, Rasterio, pystac-client, planetary-computer, scikit-learn, joblib, numpy, PyTorch (U-Net)

- 007-wave3-ai-chain: Added Python 3.12 (managed by `uv`) + FastAPI, SQLAlchemy (async) + GeoAlchemy2, scikit-learn, PyTorch, joblib, httpx, Pydantic, numpy

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
