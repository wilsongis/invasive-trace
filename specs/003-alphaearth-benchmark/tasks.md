# Tasks: Wave 1.5 - AlphaEarth Benchmark

**Input**: Design documents from `/specs/003-alphaearth-benchmark/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Tests are required for this feature because the spec requires matched-comparison validity, benchmark failure handling, and auditable recommendation outputs.

**Organization**: Tasks are grouped by user story to keep benchmark input assembly, comparison execution, and decision recording independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Services**: `app/services/`
- **ML benchmark wrapper**: `app/ml/`
- **Scripts**: `app/scripts/`
- **Tests**: `tests/unit/`, `tests/integration/`
- **Documentation evidence**: `docs/research/` or `specs/003-alphaearth-benchmark/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the benchmark-only file layout and evidence paths before cohort or model work begins.

- [x] T001 Create Wave 1.5 benchmark scaffolding in `app/services/alphaearth_client.py`, `app/services/benchmark_dataset.py`, `app/services/alphaearth_benchmark.py`, `app/services/benchmark_report.py`, `app/ml/stage2_alphaearth_benchmark.py`, and `app/scripts/run_alphaearth_benchmark.py`
- [x] T002 [P] Add any benchmark-only dependency/configuration placeholders needed in `pyproject.toml` and `.env.example` without changing the production runtime defaults
- [x] T003 [P] Add benchmark evidence output path guidance to `docs/research/` or feature-local artifacts for recommendation recording

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared benchmark access and cohort-definition infrastructure required before user stories can be implemented.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [x] T004 Create benchmark-only AlphaEarth access wrapper in `app/services/alphaearth_client.py` with logged skip behavior for auth, quota, export, and coverage failures
- [x] T005 [P] Create benchmark cohort definition and split-alignment helpers in `app/services/benchmark_dataset.py` using existing ROI/observation inputs without schema changes
- [x] T006 [P] Create experimental Stage 2 benchmark wrapper in `app/ml/stage2_alphaearth_benchmark.py` using model version `alphaearth-benchmark-v0.1.0`
- [x] T007 Create benchmark orchestration skeleton in `app/services/alphaearth_benchmark.py` that runs baseline and benchmark variants against identical cohort definitions

**Checkpoint**: Foundation ready — user story implementation can now proceed.

---

## Phase 3: User Story 1 - Assemble Benchmark Inputs (Priority: P1) 🎯 MVP

**Goal**: Assemble a matched benchmark cohort for at least one ROI/year without modifying the production ingestion path.

**Independent Test**: Run the cohort assembly workflow and confirm AlphaEarth availability is recorded, labeled observations are aligned, and unavailable coverage exits as a logged skip.

### Tests for User Story 1

- [x] T008 [P] [US1] Add unit tests in `tests/unit/test_alphaearth_client.py` covering success, auth failure, quota failure, and no-coverage skip behavior
- [x] T009 [P] [US1] Add unit tests in `tests/unit/test_benchmark_dataset.py` covering ROI/year cohort assembly and split alignment with baseline labels

### Implementation for User Story 1

- [x] T010 [US1] Implement AlphaEarth access and availability reporting in `app/services/alphaearth_client.py`
- [x] T011 [US1] Implement cohort assembly and baseline split reuse in `app/services/benchmark_dataset.py`
- [x] T012 [US1] Add CLI wiring in `app/scripts/run_alphaearth_benchmark.py` to run benchmark input assembly for a selected ROI/year cohort

**Checkpoint**: User Story 1 is complete when a matched benchmark cohort can be assembled or skipped cleanly.

---

## Phase 4: User Story 2 - Compare Baseline and AlphaEarth Variants (Priority: P2)

**Goal**: Evaluate the current Stage 2 baseline and the AlphaEarth benchmark variant on identical cohorts and emit side-by-side metrics.

**Independent Test**: Run the benchmark workflow for one cohort and confirm both variants use identical split definitions and produce comparable metrics.

### Tests for User Story 2

- [x] T013 [P] [US2] Add unit tests in `tests/unit/test_alphaearth_benchmark.py` for matched baseline-vs-benchmark evaluation behavior and metric aggregation
- [x] T014 [P] [US2] Add integration coverage in `tests/integration/test_alphaearth_benchmark_workflow.py` for end-to-end benchmark execution on a representative mocked cohort

### Implementation for User Story 2

- [x] T015 [US2] Implement the benchmark classifier wrapper in `app/ml/stage2_alphaearth_benchmark.py`
- [x] T016 [US2] Implement baseline-vs-benchmark orchestration in `app/services/alphaearth_benchmark.py`
- [x] T017 [US2] Extend `app/scripts/run_alphaearth_benchmark.py` to execute both variants and emit side-by-side precision, recall, F1, runtime, and coverage outputs

**Checkpoint**: User Story 2 is complete when a matched comparison run completes and reports side-by-side results.

---

## Phase 5: User Story 3 - Record a Go/No-Go Decision (Priority: P3)

**Goal**: Persist an auditable recommendation artifact that records whether AlphaEarth remains experimental, advances for more research, or is rejected.

**Independent Test**: Generate a recommendation artifact from benchmark results and confirm it states go/no-go/defer status without altering the production roadmap.

### Tests for User Story 3

- [x] T018 [P] [US3] Add unit tests in `tests/unit/test_benchmark_report.py` for recommendation generation from benchmark metrics and operational findings

### Implementation for User Story 3

- [x] T019 [US3] Implement recommendation/report generation in `app/services/benchmark_report.py`
- [x] T020 [US3] Persist benchmark summary evidence in `docs/research/alphaearth-benchmark-report.md` or a feature-local report artifact under `specs/003-alphaearth-benchmark/`
- [x] T021 [US3] Update `app/scripts/run_alphaearth_benchmark.py` to emit the go/no-go recommendation artifact at the end of a completed benchmark run

**Checkpoint**: User Story 3 is complete when the benchmark produces an auditable decision record.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and governance updates after the benchmark planning set exists.

- [x] T022 [P] Confirm no benchmark task modifies the contract-locked canonical schema without a separate migration-backed feature
- [x] T023 [P] Run `just verify` and resolve benchmark-planning or test regressions
- [x] T024 Record benchmark recommendation status in `AGENTS.md` Section 9 after the first completed benchmark run
- [x] T025 Validate the feature artifacts remain aligned: `spec.md`, `plan.md`, `tasks.md`, `AGENTS.md`, and `.specify/memory/constitution.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 cohort assembly
- **User Story 3 (Phase 5)**: Depends on User Story 2 benchmark results
- **Polish (Phase 6)**: Depends on all targeted user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: First deliverable — benchmark cohort assembly and availability checks
- **User Story 2 (P2)**: Depends on a valid matched cohort from US1
- **User Story 3 (P3)**: Depends on evaluation evidence from US2

### Within Each User Story

- Tests before implementation where test artifacts are specified
- AlphaEarth access before cohort assembly
- Cohort assembly before evaluation
- Evaluation before recommendation output
- Recommendation output before governance state updates

### Parallel Opportunities

- `T002` and `T003` can run in parallel during Setup
- `T005` and `T006` can run in parallel during Foundational work
- `T008` and `T009` can run in parallel for US1 test coverage
- `T013` and `T014` can run in parallel for US2 validation

---

## Implementation Strategy

### MVP First

1. Complete Phases 1-3 to prove benchmark cohort assembly or clean skip behavior
2. Stop and validate the matched-cohort workflow independently
3. Continue to comparison and decision recording only after cohort validity is confirmed

### Incremental Delivery

- Deliver User Story 1 first so the benchmark can be scoped realistically
- Add User Story 2 second to generate evidence instead of speculation
- Finish with User Story 3 so the benchmark produces an auditable recommendation
