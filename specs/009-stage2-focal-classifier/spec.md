# Feature Specification: Stage 2 Focal Classifier and Feature Extraction

**Feature Branch**: `009-stage2-focal-classifier`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: User description: "Implement Stage 2: Focal Classifier training and feature extraction. This is the critical path dependency for the AI execution chain - without Stage 2 classification, Stage 3 U-Net texture analysis cannot function properly. The project has completed Waves 0-1, Pillar II Remote Sensing, Wave 3 AI Execution Chain spec, and Wave 4 HITL Dashboard. The remaining backlog items are Stage 2 and Stage 3 ML components. Stage 2 should be prioritized because it provides the species-level spectral discrimination that feeds into all downstream AI stages."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Produce Species Predictions from ROI Inputs (Priority: P1)

As a geospatial analyst, I need Stage 2 to transform ROI-linked spectral history and confirmed observations into species-level prediction outputs so the end-to-end AI execution chain can generate usable invasive-species detections.

**Why this priority**: Stage 2 is the hard dependency that converts environmental signal into species discrimination; without it, downstream scoring and review workflows are blocked.

**Independent Test**: Can be fully tested by running Stage 2 with ROIs and available training observations, then verifying that prediction outputs include species labels and confidence scores for valid candidate locations.

**Acceptance Scenarios**:

1. **Given** an ROI with ingest-ready spectral time series and confirmed ground truth observations, **When** a Stage 2 training-and-inference run is requested, **Then** the system produces species predictions with confidence values bounded to 0.0-1.0.
2. **Given** Stage 2 prediction outputs are generated, **When** the AI execution chain requests species classifications for Stage 3 input, **Then** the system returns non-ambiguous species labels and model lineage metadata required by downstream processing.

---

### User Story 2 - Operate Resiliently on Imperfect Inputs (Priority: P2)

As an operations engineer, I need Stage 2 runs to complete safely even when scenes, observations, or external fetches are partially missing so production workflows can continue without manual recovery.

**Why this priority**: Real-world geospatial data is noisy and incomplete; resilient behavior preserves throughput and prevents single-source failures from blocking mission-critical runs.

**Independent Test**: Can be fully tested by injecting missing scenes, cloud-masked records, and transient external failures, then verifying graceful skips, bounded retries, and completion with explicit run summaries.

**Acceptance Scenarios**:

1. **Given** a Stage 2 run contains a mix of valid and unusable candidate records, **When** execution reaches invalid records, **Then** the system skips invalid inputs, logs exclusion reasons, and continues processing remaining valid records.

---

### User Story 3 - Maintain Auditability and Reproducibility (Priority: P3)

As a program lead, I need each Stage 2 run to capture reproducible training and prediction lineage so model updates and HITL feedback decisions can be audited over time.

**Why this priority**: Traceability is required for scientific defensibility, quality governance, and safe retraining decisions.

**Independent Test**: Can be fully tested by executing repeated runs against the same dataset and confirming that run artifacts and metadata provide deterministic traceability for comparisons and audits.

**Acceptance Scenarios**:

1. **Given** a completed Stage 2 run, **When** an auditor reviews run metadata, **Then** the auditor can identify input scope, training cohort characteristics, selected model version, and output summary without accessing raw execution logs.

---

### Edge Cases

- Requested ROI and date window produce zero eligible spectral records after masking and quality filters.
- Records exceed cloud tolerance and are excluded, leaving below-minimum sample counts for one or more target species.
- External fetches return HTTP 429 repeatedly; retries are exhausted and the source remains unavailable for the run.
- STAC metadata is present but one or more referenced scene assets are unreadable.
- A classifier output yields non-finite or out-of-range confidence and must be normalized or discarded before persistence.
- Ground truth labels contain rare classes with too few observations for reliable discrimination.
- Mixed-source observations provide conflicting labels for the same location and observation date.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a Stage 2 workflow that trains a focal species classifier using eligible spectral feature vectors joined to confirmed ground truth observations.
- **FR-002**: System MUST persist Stage 2 prediction outputs to the canonical prediction store with species label, confidence score, ROI linkage, geometry, timestamp, and registered Stage 2 model version.
- **FR-003**: System MUST guarantee prediction confidence values are bounded between 0.0 and 1.0 before persistence.
- **FR-004**: System MUST enforce lineage consistency by recording the Stage 2 classifier version string defined in the model registry for each prediction output.
- **FR-005**: System MUST provide Stage 3-consumable classification output for each eligible candidate location, including species label and confidence.
- **FR-006**: System MUST exclude cloud-masked or otherwise invalid spectral records from Stage 2 feature extraction and classification.
- **FR-007**: System MUST handle HTTP 429 responses from external dependencies using exponential backoff with a maximum of 3 retries, then log and skip failed records without terminating the full run.
- **FR-008**: System MUST continue processing remaining records when individual scenes, observations, or assets are missing or unreadable.
- **FR-009**: System MUST produce a run summary containing counts of processed records, skipped records (by reason), predictions generated, and failed external calls.
- **FR-010**: System MUST support reproducible reruns by storing run metadata that identifies input scope and classifier version used for the execution.

### Key Entities *(include if feature involves data)*

- **GroundTruthObservation**: Source of confirmed species labels used to build supervised training cohorts; reads confirmed observations and label attributes.
- **SpectralTimeSeries**: Source of per-scene spectral indicators and quality attributes used for feature extraction; reads index values, scene date, cloud cover, and masking flags.
- **InvasionPrediction**: Destination for Stage 2 classifier outputs; writes species label, confidence, geometry, ROI association, prediction time, and Stage 2 model version for downstream chain consumption.
- **RegionOfInterest**: Spatial scope and ownership boundary for training and inference runs; reads ROI identifiers and geometries to constrain processing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For ROI runs with sufficient training data, 100% of eligible candidate locations receive Stage 2 species classification outputs suitable for Stage 3 ingestion.
- **SC-002**: At least 95% of Stage 2 runs complete without manual intervention when exposed to expected partial-data and transient-rate-limit conditions.
- **SC-003**: 100% of persisted Stage 2 predictions include valid confidence bounds and a registered Stage 2 model version string.
- **SC-004**: Stage 2 run summaries are available for 100% of executions and include processed, skipped, and predicted record counts.
- **SC-005**: In operational validation, Stage 2 enables end-to-end AI chain execution for target ROIs with no blocker caused by missing species classification outputs.

## Assumptions

- Ground truth observation records are already synchronized and contain enough confirmed labels to train at least one viable species class per target ROI.
- Stage 2 is scoped to species classification and feature extraction only; Stage 3 texture inference behavior remains out of scope for this feature.
- Existing spectral ingestion outputs are available and follow the established quality and masking conventions.
- External data providers may be intermittently unavailable; retry-and-skip resilience is acceptable for this phase.
- Existing HITL validation workflows consume Stage 2 outputs after persistence and do not require additional UI scope in this feature.
