# Research: Stage 2 Focal Classifier and Feature Extraction

**Feature**: `specs/009-stage2-focal-classifier/`  
**Research Date**: 2026-04-07  
**Input**: Feature specification unknowns and technical context gaps  
**Notebook**: Dev notebook "gaia-atlas" (notebooklm-mcp)  
**Sources**: `/docs/research/` + geospatial ML best practices + scikit-learn documentation

---

## Decision 1: Feature Engineering Strategy—Multi-Temporal Spectral Indices + Seasonal Aggregation

**Decision**: Primary feature set = NDVI, ENDVI, Red-Edge Chlorophyll Index with temporal aggregates (min, max, mean, std deviation) over full available spectral time series per ROI, with seasonal rolling windows (3-month) and cloud masking (cloud_cover > 0.20 excluded).

**Rationale**: 
- Invasive species exhibit distinct phenological signatures in NDVI vs native grassland (earlier green-up, higher summer NDVI, later senescence)
- ENDVI and Red-Edge indices are sensitive to chlorophyll content; invasive legumes (*Bromus tectorum*) show stronger red-edge absorption
- Temporal aggregates (std dev, min/max) capture inter-annual variability differences between invaders and natives
- Seasonal rolling windows stratify signal and prevent training bias toward single season
- Cloud masking at feature stage prevents null propagation and preserves temporal continuity (Constitution V)

**Alternatives considered**:
- Raw spectral bands (B02–B12): Rejected—vegetation indices more stable across sensor/atmospheric variation
- Single annual aggregate (summer mean only): Rejected—invasive phenology spans full growing season; single-season summary loses critical differentiation
- All raw time series without aggregation: Rejected—raw daily NDVI vectors exceed feature dimensionality budget; aggregation reduces noise and training time

---

## Decision 2: Keep RandomForest as the Stage 2 baseline model
- **Decision**: Continue with scikit-learn RandomForest for Stage 2 under version `rf-v0.1.0` (from AGENTS.md Section 6).
- **Rationale**: Already integrated in runtime and artifact-loading paths, aligns with mandated classical-ML stack, and is sufficient for species-level discrimination with limited ecological labels.
  - RandomForest: Low hyperparameter sensitivity; robust to mixed feature scales; fast inference (ensemble mean << boosting iterations)
  - Benchmark comparison: Train XGBoost in parallel; promote only if ≥5% absolute F1 improvement with <2× inference latency
- **Alternatives considered**:
  - XGBoost: Viable but adds model-specific tuning/operational overhead; benchmark comparison preferred
  - SVM: Rejected—kernel tuning time-intensive; RandomForest simpler to deploy
  - Deep neural networks: Rejected—spectral feature count (~12–15) too low to justify deep learning overhead; U-Net moved to Stage 3

---

## Decision 3: Handling Imbalanced Species Classes—Stratified Sampling + Class Weights + F1-Balanced Metrics

**Decision**: Train/test split stratified by species label; apply class_weight='balanced' in RandomForest; validate using Precision, Recall, F1-macro (not accuracy); enforce minimum 10 confirmed observations per target species.

**Rationale**:
- Invasive observation counts vary widely: common invaders (e.g., *Bromus tectorum*) have tens; rare range-extensions <5 per ROI
- Stratified sampling prevents train/test species distribution mismatch; class_weight='balanced' automatically scales minority-class loss
- F1-macro equally weights all species; prevents well-represented species from dominating metrics
- 10-observation minimum avoids statistical noise; defer rare classes until next HITL retraining batch (≥50 validated/rejected, per AGENTS.md Section 6)

**Alternatives considered**:
- SMOTE (oversampling): Rejected—sparse ecological data; synthetic samples add no information
- Threshold-moving: Rejected—RandomForest ensembles don't benefit; class_weight more principled
- Ignore minority classes: Rejected—invasive species of interest are often rare

---

## Decision 4: Training Cohort Assembly Must Be Deterministic and Quality-Gated

**Decision**: Build Stage 2 cohorts only from unmasked spectral records joined to confirmed observations; apply deterministic ordering and label assignment policy; skip invalid/incomplete records with warning logs.

**Rationale**: 
- Deterministic cohorts required for reproducibility and reliable run-to-run comparisons under HITL governance (Spec R3)
- Skipping masking invalid records preserves signal quality and prevents classifier bias

**Alternatives considered**:
- Opportunistic sampling with random join: Rejected—introduces non-repeatable model behavior
- Including masked/partial spectral rows: Rejected—degrades classifier signal and violates quality intent

---

## Decision 5: Candidate Location Strategy—ROI Centroid + Deterministic Spatial Grid

**Decision**: Primary inference point = ROI centroid (ST_Centroid); secondary grid = deterministic regular 500m spacing tessellating ROI bounding box, filtered to points within ROI polygon (ST_Intersects). Same seed for all runs to ensure reproducibility.

**Rationale**:
- ROI centroid balances representativeness and simplicity
- 500m grid matches Sentinel-2 resolution (~50×50 10m pixels per cell), reduces noise while preserving heterogeneity
- Deterministic grid ensures reproducible results across retraining cycles (auditable inference runs)
- Grid density (~400–500 points for 10×10km ROI) computationally tractable and meets latency budget (<2s per ROI)

**Alternatives considered**:
- Random sample for each run: Rejected—violates reproducibility requirement (Spec R3)
- Finer grid (250m): Rejected—2000–4000 points per ROI exceeds latency budget
- NDVI anomaly peaks only: Rejected—creates circular dependency; Stage 1 must precede Stage 2

---

## Decision 6: Stage 2 Feature Vectors Require Explicit Validity Filtering

**Decision**: Feature assembly skips records that cannot produce complete spectral features; elevation fetch failures fallback to 0.0 with warning logs. No silently invalid spectral features injected into models.

**Rationale**: 
- Avoids silent bias from invalid spectral data
- External transient failures don't block entire run (resilient-by-default, Constitution V)

**Alternatives considered**:
- Zero-impute all missing values: Rejected—can bias model behavior and hide data quality defects
- Fail entire run on first invalid record: Rejected—violates resilience requirement

---

## Decision 7: Preserve Existing API Surface; Strengthen Behavior

**Decision**: Do not add new HTTP endpoints in this feature. Stage 2 behavior surfaced through existing pipeline execution and prediction retrieval paths (existing `/api/v1/predictions` infrastructure from Wave 4 HITL dashboard).

**Rationale**: Minimizes integration risk; keeps feature focused on critical-path classifier dependency.

**Alternatives considered**:
- Dedicated Stage 2 training API: Rejected—script-driven training adequate and operationally simpler

---

## Decision 8: No Schema Migration in This Planning Cycle

**Decision**: Stage 2 implementation uses canonical schema as-is; lineage captured through `model_version` field (= `rf-v0.1.0`) and run summaries/logs.

**Rationale**: Required fields already exist in `invasion_predictions` and supporting tables (Constitution IV).

**Alternatives considered**:
- New run audit table: Rejected—avoid unnecessary schema expansion before Stage 2 core reliability delivered

---

## Decision 9: Cross-Validation and Performance Thresholds—Stratified 5-Fold + F1-Macro ≥ 0.50

**Decision**: Train/test split 70%/30% (stratified by species); 5-fold stratified k-fold cross-validation on training set; primary metric F1-macro (secondary: Precision, Recall, Balanced Accuracy macro-averaged); production readiness threshold = F1-macro ≥ 0.50 on held-out test set.

**Rationale**:
- Stratified k-fold prevents class imbalance from skewing fold statistics
- F1-macro treats rare species equally; does not mask poor performance on minority invaders
- 0.50 threshold balances false positive/negative cost; HITL reviewer corrects both; slightly-better-recall bias acceptable
- 70/30 split standard for typical feature count (~12–15)

**Alternatives considered**:
- Leave-One-Out CV: Rejected—computationally expensive for 1000+ records; 5-fold sufficient
- F1-weighted: Rejected—over-weights common species; F1-macro ensures rare invaders equal importance
- 0.80 threshold: Rejected—unrealistic for geospatial spectral classification (rarely >0.70 F1)
- 0.30 threshold: Rejected—below random guessing; unusable for operational deployment

---

## Decision 10: Feature Dimensionality—12–15 Features (NDVI/ENDVI/Red-Edge Aggregates) + Optional PCA

**Decision**: Core features = NDVI (min, max, mean, std_dev) + ENDVI (min, max, mean, std_dev) + Red-Edge Chlorophyll Index (min, max, mean, std_dev) = 12 features. Optional seasonal expansion (Q1–Q4 rolling means for NDVI) = up to 16 features. Optional PCA down to 10 principal components if feature correlation > 0.85.

**Rationale**:
- 12–15 features optimal for RandomForest on ~1000 training samples; avoids curse of dimensionality while preserving separability
- Temporal aggregates capture invasive phenological distinctiveness without raw time series complexity
- Red-Edge indices weak but additive; improves class separation for invasive legumes without overfitting
- PCA optional; RandomForest robustness to correlated features is high, but interpretation lost with PCA
- z-score standardization ensures consistent hyperparameters across different ROIs

**Alternatives considered**:
- All raw Sentinel-2 bands (B02–B12): Rejected—11+ bands reduce feature importance interpretability; no ensemble benefit
- Temporal derivatives: Rejected—adds complexity and noise for marginal gain
- Tasseled Cap: Rejected—NDVI/ENDVI adequate; adds complexity without proven invasive species benefit

---

## Decision 11: Production Deployment Strategy—Joblib Serialization + Model Card + Version-Locked Artifacts

**Decision**: Model serialization = joblib (scikit-learn standard) stored at `./models/FocalClassifier/rf-v0.1.0/classifier.pkl` + `metadata.json` (training date, feature names, class labels, training sample counts, CV F1-macro, class_weight config). Version string from AGENTS.md Section 6 (`rf-v0.1.0`); next iteration = `rf-v0.2.0` after successful HITL retraining. Inference latency target = <2s per ROI (500 candidate points, single-threaded).

**Rationale**:
- Joblib human-readable; preserves RandomForest structure exactly; no compatibility surprises
- Model card ensures any user understands training context without re-reading code (governance + regulatory compliance)
- Version locking makes prediction lineage auditable; any prediction traceable to training cohort
- <2s latency budget 10× faster than STAC query (5s), 100× faster than training (30s); acceptable for operational dashboards

**Alternatives considered**:
- ONNX format: Rejected—cross-platform serialization adds complexity for Python-only deployment
- In-memory caching: Rejected—model state must persist across server restarts
- No versioning: Rejected—prior run comparisons and rollback capability required for HITL validation

---

## Decision 12: Preflight and Verification Gates Are Mandatory

**Decision**: Implementation runbook requires `just research-sync`, `just research-test`, `just lint`, `just test`, and `just verify`. All gates must pass before merge.

**Rationale**: Enforces constitution and stack compliance; provides deterministic quality gates (Constitution II).

---

## Research Summary: Unknowns → Resolved

| Unknown | Resolution |
|---------|-----------|
| Optimal feature set? | NDVI + ENDVI + Red-Edge indices with temporal aggregates (min/max/mean/std dev, 12–15 features total) |
| RandomForest or XGBoost? | RandomForest primary (`rf-v0.1.0`); XGBoost benchmark; promote only if ≥5% F1 lift |
| Imbalanced species handling? | Stratified sampling + `class_weight='balanced'` + F1-macro metrics + 10-observation minimum per species |
| Candidate locations? | ROI centroid + deterministic 500m spatial grid; reproducible across runs |
| Inference latency budget? | <2s per ROI (typical 500 candidate points, single-threaded) |
| Model versioning? | Joblib serialization + model card; version string from AGENTS.md Section 6 (`rf-v0.1.0`) |
| Performance threshold? | F1-macro ≥ 0.50 on held-out test set for production readiness |
| Feature count & scaling? | 12–15 features; z-score normalization; optional PCA to 10 components if correlated |
| Cross-validation strategy? | 5-fold stratified k-fold (70% train / 30% test); respect spatial clustering considerations in Wave 4 |
| External API errors? | Exponential backoff (3 retries) + log + skip per Constitution V; resilient execution semantics |

