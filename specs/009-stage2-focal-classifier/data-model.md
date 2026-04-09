# Data Model: Stage 2 Focal Classifier and Feature Extraction

**Feature**: `specs/009-stage2-focal-classifier/`  
**Design Date**: 2026-04-07  
**Input**: Feature specification requirements + research.md decisions  
**Canonical Tables**: See AGENTS.md Section 4

---

## Overview

Stage 2 consumes existing canonical entities and does not introduce new tables in this scope. Data flow moves from spectral and observation records into classifier outputs persisted in `invasion_predictions`. All training data is derived from existing tables via deterministic queries.

---

## Entities

### 1. Stage2TrainingCandidate (Derived View, Not Persisted)

**Purpose**: Provides supervised rows for Stage 2 RandomForest training.

**Source Tables**: 
- `spectral_time_series` (unmasked Sentinel-2 indices)
- `regions_of_interest` (ROI geometry context)
- `ground_truth_observations` (confirmed species labels)

**Attributes**:
```
- record_id: UUID (from ground_truth_observations)
- roi_id: UUID (parent ROI)
- species_label: TEXT (target class for training)
- observation_date: DATE (when species was observed)
- observation_geom: POINT (SRID 4326)

-- Spectral feature aggregates (temporal, min/max/mean/std over 3-month window)
- ndvi_min, ndvi_max, ndvi_mean, ndvi_std: FLOAT
- endvi_min, endvi_max, endvi_mean, endvi_std: FLOAT
- red_edge_min, red_edge_max, red_edge_mean, red_edge_std: FLOAT

- scene_count: INT (number of unmasked scenes in aggregation window)
```

**Validation Rules** (from research.md Decision 3, Decision 4):
- `is_masked` must be FALSE for all contributing `spectral_time_series` rows
- All 12 spectral features must be finite (not NaN, not infinite); skip records with invalid features
- `species_label` must be confirmed (from `ground_truth_observations.is_confirmed = TRUE`)
- Minimum 3 unmasked scenes required per observation (Scene count ≥ 3)
- Species must have ≥10 total training observations per ROI to be included (research.md Decision 3)

**Query Template** (Pseudo-SQL):
```sql
-- Deterministic 3-month temporal window around each observation
SELECT
  gto.id as record_id,
  roi.id as roi_id,
  gto.species_label,
  gto.observed_at as observation_date,
  gto.geom as observation_geom,
  
  -- 12 spectral features from 3-month window
  MIN(sts.ndvi), MAX(sts.ndvi), AVG(sts.ndvi), STDDEV(sts.ndvi),
  MIN(sts.endvi), MAX(sts.endvi), AVG(sts.endvi), STDDEV(sts.endvi),
  MIN(sts.red_edge), MAX(sts.red_edge), AVG(sts.red_edge), STDDEV(sts.red_edge),
  
  COUNT(sts.id) as scene_count
  
FROM ground_truth_observations gto
JOIN regions_of_interest roi ON ST_Contains(roi.geom, gto.geom)
LEFT JOIN spectral_time_series sts ON (
  sts.roi_id = roi.id
  AND sts.is_masked = FALSE
  AND sts.scene_date BETWEEN gto.observed_at - INTERVAL '45 days' 
                         AND gto.observed_at + INTERVAL '45 days'
)
WHERE gto.is_confirmed = TRUE
GROUP BY gto.id, gto.species_label, gto.geom, gto.observed_at, roi.id
HAVING COUNT(sts.id) >= 3  -- Minimum scene threshold
```

---

### 2. CandidateLocation (Derived, Ephemeral)

**Purpose**: Deterministic set of inference points within an ROI (centroid + grid).

**Generation Strategy** (from research.md Decision 5):
- Primary point: ROI centroid (ST_Centroid)
- Secondary grid: Deterministic 500m spacing lattice within ROI bounding box, filtered by ST_Intersects
- Typical output: 1 centroid + 400–500 grid points per 10×10km ROI

**Attributes**:
```
- candidate_id: UUID (runtime-generated)
- roi_id: UUID (parent ROI)
- geom: POINT (SRID 4326, centroid or grid node)
- source_type: TEXT ('centroid' or 'grid')
- grid_index: TUPLE (row, col) of grid cell (NULL for centroid)
```

**Determinism Contract** (from research.md Decision 5):
- Identical ROI geometry → identical candidate set across multiple inference runs
- Same grid seed across all runs (reproducible)
- Enables auditability (Spec R3: "Maintain Auditability and Reproducibility")

---

### 3. Stage2InferenceVector (Runtime Object, Not Persisted)

**Purpose**: Input feature vector for RandomForest classifier prediction on a single candidate location.

**Source**: For each `CandidateLocation`:
1. Retrieve all unmasked `spectral_time_series` rows for the candidate's ROI
2. Temporal window: Full available time series (no windowing; different from training)
3. Compute feature aggregates: min, max, mean, stddev for NDVI, ENDVI, Red-Edge
4. Stack into 12-element feature vector

**Attributes**:
```
- candidate_id: UUID (parent CandidateLocation)
- features: ARRAY[12] (
    ndvi_min, ndvi_max, ndvi_mean, ndvi_std,
    endvi_min, endvi_max, endvi_mean, endvi_std,
    red_edge_min, red_edge_max, red_edge_mean, red_edge_std
  )
- scene_count: INT (number of contributing unmasked scenes)
```

**Validation Rules** (from research.md Decision 6):
- All feature values must be finite (not NaN, not infinite)
- If any feature is invalid, skip candidate and log warning (strict validation; no fallback)
- Minimum 3 unmasked scenes required for feature extraction

---

### 4. InvasionPrediction (Canonical Persisted Output)

**Table**: `invasion_predictions` (canonical, see AGENTS.md Section 4)

**Fields Written by Stage 2**:
```
- id: UUID PRIMARY KEY (generated)
- roi_id: UUID REFERENCES regions_of_interest (from CandidateLocation)
- species_label: TEXT NOT NULL (from classifier.predict())
- confidence: FLOAT NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0) (from classifier.predict_proba())
- hotspot_score: FLOAT NULL (Stage 3 responsibility; NULL from Stage 2)
- geom: GEOMETRY(POINT, 4326) NOT NULL (from CandidateLocation.geom)
- model_version: TEXT NOT NULL (= 'rf-v0.1.0' from AGENTS.md Section 6)
- predicted_at: TIMESTAMPTZ DEFAULT now() (insertion timestamp)
- validated: BOOLEAN NULL (NULL=pending HITL review, TRUE=confirmed, FALSE=rejected)
- validator_notes: TEXT NULL (populated after HITL action)
```

**Validation Rules** (from Constitution IV, research.md Decision 11):
- `confidence` MUST satisfy `CHECK (confidence BETWEEN 0.0 AND 1.0)` at DB layer
  - Before INSERT: Clip any out-of-range predictions to [0.0, 1.0]
- `model_version` MUST exactly match a registered version in AGENTS.md Section 6
  - Current: `rf-v0.1.0` (from AGENTS.md Section 6, research.md Decision 2)
- `validated` tristate:
  - NULL: pending HITL review (initial state)
  - TRUE: HITL confirmed invasive
  - FALSE: HITL rejected (not invasive or incorrect species)
- `geom` MUST use SRID 4326
- `roi_id` MUST reference a valid `regions_of_interest.id`

**Indexing** (for HITL dashboard + downstream queries):
```sql
CREATE INDEX idx_pred_geom   ON invasion_predictions USING GIST (geom);
CREATE INDEX idx_pred_roi    ON invasion_predictions (roi_id);
CREATE INDEX idx_pred_score  ON invasion_predictions (hotspot_score DESC);
```

---

### 5. ModelArtifact (File-Based, Not a Table)

**Purpose**: Trained RandomForest classifier + metadata for reproducible inference.

**Storage Location**: `./models/FocalClassifier/rf-v0.1.0/`

**Contents**:
```
classifier.pkl              # Joblib-serialized RandomForest
metadata.json               # Training metadata (see below)
feature_names.txt           # 12 ordered feature column names
class_labels.txt            # Ordered target species classes
README.md                   # Model card
```

**metadata.json Structure** (from research.md Decision 11):
```json
{
  "model_version": "rf-v0.1.0",
  "model_type": "RandomForest",
  "training_date": "2026-04-07T14:30:00Z",
  "training_roi_ids": ["uuid-1", "uuid-2"],
  "training_sample_count": 1250,
  "training_sample_count_by_species": {
    "Bromus tectorum": 450,
    "Tamarix ramosissima": 320,
    "Lepidium latifolium": 480
  },
  "feature_names": [
    "ndvi_min", "ndvi_max", "ndvi_mean", "ndvi_std",
    "endvi_min", "endvi_max", "endvi_mean", "endvi_std",
    "red_edge_min", "red_edge_max", "red_edge_mean", "red_edge_std"
  ],
  "class_labels": ["Bromus tectorum", "Tamarix ramosissima", "Lepidium latifolium"],
  "hyperparameters": {
    "n_estimators": 100,
    "max_depth": 15,
    "min_samples_leaf": 5,
    "class_weight": "balanced"
  },
  "cv_results": {
    "mean_f1_macro": 0.516,
    "test_f1_macro": 0.518,
    "test_precision_macro": 0.530,
    "test_recall_macro": 0.510,
    "test_balanced_accuracy": 0.512
  }
}
```

**Validation Rules** (from research.md Decision 11):
- `model_version` must exist in AGENTS.md Section 6
- CV F1-macro ≥ 0.50 required for production (research.md Decision 9)
- Feature count must match `len(feature_names)` (exactly 12)
- All metadata fields required; no NULL fields

---

## Data Relationships

```
┌──────────────────────────────────────────────────────────────────┐
│                  Training Data Flow                               │
└──────────────────────────────────────────────────────────────────┘

  ground_truth_observations          spectral_time_series
        (confirmed labels)                 (indices)
           + filtering                    + filtering
              ↓                                ↓
              └────────────────┬──────────────┘
                              ↓
                    Stage2TrainingCandidate
                   (12 spectral features per
                    confirmed observation)
                              ↓
      ┌──────────────────────────────────────────┐
      │ RandomForest.fit(X_train, y_train)        │
      │ X_train: (N, 12) feature matrix           │
      │ y_train: (N,) species labels              │
      │ class_weight='balanced' (handle imbalance)│
      │ Output: trained classifier                │
      └──────────────────────────────────────────┘
                              ↓
                       ModelArtifact
                  (./models/FocalClassifier/rf-v0.1.0/)

┌──────────────────────────────────────────────────────────────────┐
│                  Inference Data Flow                              │
└──────────────────────────────────────────────────────────────────┘

  regions_of_interest (ROI geom)  spectral_time_series
              ↓                           ↓
              └────────────┬──────────────┘
                          ↓
          CandidateLocation Generator
         (centroid + 500m deterministic grid)
                          ↓
        (for each candidate_location):
              ├─→ Extract Stage2InferenceVector
              │   (12 spectral features full time series)
              ├─→ classifier.predict(vector)
              │   → species_label
              └─→ classifier.predict_proba(vector)
                  → confidence scores
                          ↓
                  prediction_output
            (species_label, confidence)
                          ↓
              InvasionPrediction
          (write to invasion_predictions table
           with model_version='rf-v0.1.0',
           validated=NULL, geom=POINT)
```

---

## State Transitions

### Training Execution
```
IDLE
  ↓
ASSEMBLING_COHORT
  (query ground_truth_observations + spectral_time_series)
  ↓
VALIDATING_COHORT
  (check feature completeness, min scene count, species count)
  ├→ FAILURE: log errors, skip ROI
  ↓
TRAINING
  (RandomForest.fit with class_weight='balanced')
  ├→ FAILURE: log training error, retain previous version
  ↓
EVALUATING (5-fold stratified CV + test metrics)
  ├→ CV F1-macro < 0.50: log warning, model archived as-is
  ↓
SUCCESS
  (model_artifact written to ./models/FocalClassifier/rf-v0.1.0/)
  (metadata.json records CV metrics, training date, sample counts)
```

### Prediction Lifecycle (per invasion_predictions record)
```
validated = NULL  (inserted by Stage 2, pending HITL review)
    ↓
[HITL reviewer examines prediction + context in dashboard]
    ↓
    ├→ validated = TRUE   (confirmed invasive, correct species)
    │     ↓
    │     [accumulate feedback batch]
    │     ↓
    │     [batch ≥ 50 validated records]
    │     ↓
    │     [trigger retraining: Stage2.train() → rf-v0.2.0]
    │
    └→ validated = FALSE  (not invasive or incorrect species)
          ↓
          [accumulate feedback batch]
          [batch ≥ 50 validated records]
          [trigger retraining]
```

---

## Assumptions & Constraints

**Training Data Availability** (research.md Decision 3):
- Each target ROI requires ≥10 confirmed observations per species
- ROIs with insufficient data per species skip Stage 2 for that species (logged)

**Spectral Coverage**:
- Spectral time series should span ≥12 months for robust feature aggregation
- Require ≥30% unmasked scenes (cloud_cover ≤ 0.20) for reliable temporal features
- ROIs below thresholds flagged in training summary

**Feature Completeness** (research.md Decision 6):
- All 12 features must be computable and finite for both training and inference
- Records with NaN or infinite features skipped with warning logs

**Species Taxonomy**:
- Target invasive species list managed externally (config)
- Stage 2 only predicts species in taxonomy
- Unknown species in ground truth logged but excluded from training

**Retraining Trigger** (AGENTS.md Section 6):
- Batch ≥50 validated/rejected predictions triggers retraining candidate
- Current model (`rf-v0.1.0`) continues serving until new version validated
- Version bump: `rf-v0.2.0` follows `rf-v0.1.0` after successful retraining
  - confidence must be within [0.0, 1.0] before persistence.
  - model_version must equal rf-v0.1.0.
  - geom must remain POINT SRID 4326.
  - validated defaults to null for new predictions.

## Relationships

- regions_of_interest (1) -> (many) spectral_time_series
- regions_of_interest (1) -> (many) invasion_predictions
- ground_truth_observations provides label source for Stage2TrainingCandidate
- spectral_time_series provides temporal spectral feature source for both training and inference

## State Transitions

### Training lifecycle
1. Candidate extraction: collect eligible Stage2TrainingCandidate rows.
2. Validation: drop incomplete or invalid candidates.
3. Fit: train RandomForest model artifact at models/FocalClassifier/rf-v0.1.0/classifier.pkl.
4. Publish: artifact available for runtime load.

### Inference lifecycle
1. Candidate selection from unmasked spectral rows.
2. Feature extraction and enrichment to Stage2InferenceVector.
3. Classification yields species_label and confidence.
4. Confidence clamp and persistence into invasion_predictions.
5. Pipeline summary includes created/skipped counters.

## Invariants

- No canonical schema mutation is required for Stage 2 plan scope.
- Stage 2 model version string remains registry-locked to rf-v0.1.0.
- Stage 2 must remain resilient: invalid single candidates never abort full run.
