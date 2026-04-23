# Product Context: Invasive Trace

## Why This Project Exists
Invasive plant species (e.g., *Bromus tectorum*, cheatgrass) degrade native grassland ecosystems managed by the Southern Grassland Institute. Manual field surveys are expensive and infrequent. This system automates early detection using satellite imagery and ML to enable proactive land management.

## Problems It Solves
1. **Detection lag** — Manual surveys miss early-stage invasion windows; multi-temporal NDVI anomaly detection catches green-up departure before visual confirmation is feasible.
2. **Classification ambiguity** — Spectral similarity between native and invasive species is resolved by a trained focal classifier (RandomForest/XGBoost) on curated spectral feature vectors.
3. **Spatial prioritization** — U-Net hotspot scoring ranks spread risk so field crews focus on highest-impact areas first.
4. **Ground truth gap** — iNaturalist and EDDMapS records are ingested automatically to maintain an up-to-date observation layer without manual data entry.
5. **Validation bottleneck** — The HITL dashboard lets domain experts confirm or reject AI predictions, closing the human feedback loop and triggering model retraining at ≥50 validated/rejected events.

## How It Should Work (User Flow)
1. SGI staff define a **Region of Interest (ROI)** polygon via the API or dashboard.
2. The system queries Planetary Computer for Sentinel-2 scenes within the ROI, computes spectral indices, and stores them in `spectral_time_series`.
3. **Stage 1** (AnomalyDetector) flags scenes with unusual NDVI temporal signatures.
4. **Stage 2** (FocalClassifier `rf-v0.1.0`) classifies anomalous pixels to species label + confidence.
5. **Stage 3** (UNetTexture `unet-v0.1.0`) scores spatial spread risk → `hotspot_score` stored in `invasion_predictions`.
6. The **HITL Dashboard** (Leaflet + HTMX) renders prediction cards; validators approve/reject each prediction.
7. Once ≥50 feedback events accumulate, `check_retrain_trigger()` emits `RETRAINING_TRIGGERED` for the next training cycle.

## User Experience Goals
- API-first: all data flows accessible via REST endpoints
- Dashboard is minimal but functional — Leaflet map + prediction card list, no JS framework overhead
- Zero unhandled errors from external API failures — graceful degradation always
- Predictions are spatially precise (WGS84 point geometry, deterministic ROI-centroid fallback)