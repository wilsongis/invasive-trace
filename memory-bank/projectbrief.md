# Project Brief: Invasive Trace

## Core Objective
Detect, classify, and map invasive plant species across Southern Grassland Institute (SGI) study areas using multi-temporal remote sensing, spectral analysis, and a three-stage AI execution chain.

## Client
Southern Grassland Institute (SGI)

## Scope
- Ingest multi-temporal satellite imagery (Sentinel-2, Landsat HLS, NAIP) via Microsoft Planetary Computer STAC
- Compute spectral indices (NDVI, ENDVI, Red-Edge) for temporal anomaly detection
- Classify invasive species at pixel/point level using a focal ML classifier
- Score ecological spread risk via spatial texture model (U-Net)
- Expose predictions through a HITL (Human-in-the-Loop) validation dashboard
- Persist all spatial data in PostGIS with full lineage

## Non-Goals
- No React/Vue/Svelte frontend
- No SQLite/MongoDB
- No Docker Desktop (Podman only)
- AlphaEarth embeddings are benchmark-only; not for production Stage 2

## Quality Gate
`just verify` must pass (ruff clean + all pytest tests) before any pillar is considered complete.