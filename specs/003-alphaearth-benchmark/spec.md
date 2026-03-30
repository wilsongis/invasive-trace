# Feature Specification: Wave 1.5 - AlphaEarth Benchmark

**Feature Branch**: `003-alphaearth-benchmark`  
**Created**: 2026-03-27  
**Status**: Draft  
**Input**: User description: "Wave 1.5 AlphaEarth benchmarking proposal covering AGENTS alignment, constitution amendment, and a benchmark-only feature spec."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assemble Benchmark Inputs (Priority: P1)

As a contributor evaluating AlphaEarth for invasive-species detection, I need a repeatable way to assemble benchmark-ready inputs for the same ROI and label set used by the Stage 2 baseline so I can compare models without changing the production pipeline.

**Why this priority**: The benchmark is only credible if the comparison dataset is aligned to the current baseline. Without a matched input cohort, every downstream result is suspect.

**Independent Test**: Can be fully tested by selecting at least one ROI/year cohort, retrieving AlphaEarth annual embeddings for covered geography, and confirming the benchmark dataset aligns with the same observations and train/test split used for the Stage 2 baseline.

**Acceptance Scenarios**:

1. **Given** a benchmark ROI and year are defined, **When** AlphaEarth coverage is queried for that cohort, **Then** the system records whether annual embeddings are available without modifying the production STAC ingestion flow.
2. **Given** AlphaEarth embeddings are available for the cohort, **When** the benchmark dataset is assembled, **Then** it aligns to the same labeled ground-truth observations used by the baseline Stage 2 classifier.
3. **Given** AlphaEarth embeddings are unavailable or access fails, **When** the benchmark input step runs, **Then** the run exits cleanly with a logged reason and the production roadmap remains unblocked.

---

### User Story 2 - Compare Baseline and AlphaEarth Variants (Priority: P2)

As a technical lead deciding whether AlphaEarth is worth further investment, I need a controlled comparison between the current Stage 2 classifier and an AlphaEarth-based benchmark variant so I can judge any accuracy gain against added dependency cost and operational complexity.

**Why this priority**: The entire point of Wave 1.5 is evidence, not enthusiasm. A matched comparison is the minimum standard for a defensible decision.

**Independent Test**: Can be fully tested by training or evaluating the baseline `rf-v0.1.0` configuration and an AlphaEarth benchmark variant on identical splits, then recording metric deltas and runtime/dependency observations.

**Acceptance Scenarios**:

1. **Given** a matched benchmark cohort exists, **When** the baseline and AlphaEarth variants are evaluated, **Then** both runs use identical ROI, label set, and train/test split definitions.
2. **Given** both variants complete evaluation, **When** metrics are summarized, **Then** precision, recall, F1, runtime, and dependency burden are reported side by side.
3. **Given** the AlphaEarth variant underperforms or adds unacceptable operational overhead, **When** the results are reviewed, **Then** the benchmark concludes without changing the production baseline.

---

### User Story 3 - Record a Go/No-Go Decision (Priority: P3)

As a project maintainer, I need a written decision artifact that captures whether AlphaEarth should remain experimental, advance to another spike, or be rejected so later roadmap changes are grounded in evidence rather than memory.

**Why this priority**: Without a decision record, the team will revisit the same architectural question repeatedly and risk introducing undocumented drift into AGENTS, the constitution, or the roadmap.

**Independent Test**: Can be fully tested by producing a benchmark summary that states the recommendation, cites the comparison evidence, and explicitly confirms whether production adoption is deferred or proposed for a future amendment.

**Acceptance Scenarios**:

1. **Given** benchmark evidence exists, **When** the decision record is written, **Then** it explicitly states go, no-go, or continue-research status.
2. **Given** the decision is no-go or deferred, **When** roadmap artifacts are reviewed, **Then** the production Planetary Computer baseline remains unchanged.
3. **Given** the decision is go-for-further-planning, **When** a follow-on proposal is drafted, **Then** it references the benchmark evidence before suggesting any production pipeline amendment.

### Edge Cases

- AlphaEarth annual coverage does not exist for the selected ROI/year, leaving no valid benchmark cohort.
- Earth Engine authentication, quota, or requester-pays export setup fails before embeddings can be accessed.
- AlphaEarth embeddings are available, but their annual cadence cannot be aligned to Stage 1 phenology or scene-level cloud masking.
- Embedding dimensionality, projection, or join logic does not match the expected benchmark feature assembly path.
- AlphaEarth improves one quality metric but materially worsens runtime, dependency burden, or reproducibility.
- Benchmark evidence is incomplete or uses a different train/test split than the baseline, making the comparison invalid.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Wave 1.5 MUST preserve the current Planetary Computer STAC and scene-level spectral pipeline as the production baseline throughout the benchmark.
- **FR-002**: The benchmark MUST retrieve AlphaEarth data only through an approved benchmark access path and MUST treat auth, quota, coverage, or export failures as non-fatal benchmark skips.
- **FR-003**: The benchmark MUST evaluate an AlphaEarth-based Stage 2 comparison variant against the registered baseline classifier `rf-v0.1.0` using identical ROI, label set, and train/test split definitions.
- **FR-004**: The benchmark MUST NOT use AlphaEarth annual embeddings for Stage 1 temporal anomaly detection, cloud masking, or any other phenology-sensitive production logic.
- **FR-005**: The benchmark MUST record side-by-side precision, recall, F1, runtime, dependency burden, and data-coverage findings for every completed comparison run.
- **FR-006**: The benchmark MUST produce a written go/no-go recommendation before any future artifact proposes AlphaEarth as a production input source.
- **FR-007**: Benchmark artifacts MUST avoid changing the contract-locked canonical PostGIS schema unless a separate migration-backed feature specification is approved.
- **FR-008**: Any benchmark implementation MUST leave existing Wave 1 and Wave 2 roadmap work unblocked when AlphaEarth inputs are unavailable or unsuitable.
- **FR-009**: Benchmark evidence MUST be recorded in repository artifacts so the decision can be audited without relying on chat history or memory.

### Key Entities *(include if feature involves data)*

- **Benchmark Cohort Definition**: The ROI, year, label set, and train/test split used to ensure the baseline and AlphaEarth variants are evaluated on identical conditions.
- **AlphaEarth Embedding Sample**: The annual 64-dimensional embedding input associated with a covered spatial cohort and used only for benchmark comparison work.
- **Stage 2 Baseline Result**: The evaluation output from the registered `rf-v0.1.0` classifier on the benchmark cohort.
- **Benchmark Comparison Report**: The artifact that records metrics, runtime, operability findings, coverage constraints, and the final go/no-go recommendation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least one representative ROI/year benchmark cohort is evaluated with both the baseline and AlphaEarth comparison variants using identical split definitions.
- **SC-002**: 100% of completed benchmark runs produce a comparison report containing precision, recall, F1, runtime, dependency burden, and coverage findings.
- **SC-003**: 100% of AlphaEarth auth, quota, export, or coverage failures exit as logged benchmark skips without blocking the existing production roadmap.
- **SC-004**: A written go/no-go recommendation is recorded before any production adoption task for AlphaEarth is added to the roadmap.
- **SC-005**: AlphaEarth is considered eligible for future promotion only if it demonstrates a measurable improvement over the baseline on the benchmark cohort and does not invalidate the constitution-locked production architecture.

## Assumptions

- Wave 1.5 is a research spike focused on Stage 2 benchmark comparison, not a production architecture replacement.
- The current Stage 1 anomaly detector and Planetary Computer scene-ingestion path remain the canonical production design unless a later amendment explicitly changes them.
- Access to an approved AlphaEarth benchmark source can be obtained for at least one representative ROI/year cohort, even if broader coverage remains incomplete.
- Benchmark results can be evaluated using the project's existing ground-truth observations and do not require canonical schema changes during the initial spike.
- Any implementation planning for this feature will add plan/tasks artifacts later; this spec defines the benchmark scope and decision rules only.

## Out of Scope

- Replacing the production Planetary Computer STAC ingestion workflow.
- Replacing or redesigning the Stage 1 NDVI anomaly detector.
- Introducing AlphaEarth-driven changes to the contract-locked canonical database schema in this wave.
- Declaring AlphaEarth a production dependency without a subsequent amendment backed by benchmark evidence.
