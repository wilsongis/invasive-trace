# Implementation Plan: Wave 1.5 - AlphaEarth Benchmark

**Branch**: `003-alphaearth-benchmark` | **Date**: 2026-03-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-alphaearth-benchmark/spec.md`

**Note**: This plan is intentionally benchmark-scoped. It evaluates AlphaEarth as an experimental Stage 2 feature source without changing the production Planetary Computer baseline, the Stage 1 anomaly path, or the canonical schema.

## Summary

Wave 1.5 adds a controlled benchmark lane for AlphaEarth annual embeddings. The implementation will validate access and coverage for at least one ROI/year cohort, assemble a benchmark dataset matched to the existing Stage 2 baseline labels and train/test splits, evaluate a benchmark classifier variant against `rf-v0.1.0`, and produce a written go/no-go recommendation. The work is non-blocking by design: any AlphaEarth auth, quota, export, or coverage failure is logged as a skipped benchmark run and leaves the production roadmap unchanged.

## Technical Context

**Language/Version**: Python 3.12 (managed by `uv`)
**Primary Dependencies**: FastAPI, SQLAlchemy (async) + GeoAlchemy2, httpx, scikit-learn, pytest, pytest-asyncio, pystac-client, planetary-computer
**Storage**: PostgreSQL 16 + PostGIS 3.4 — benchmark reads existing canonical tables and writes no new production schema by default
**Testing**: `pytest` + `pytest-asyncio` via `just test`
**Target Platform**: Podman-containerized Linux (macOS dev via `just run`)
**Project Type**: Geospatial AI web service with research-spike benchmark workflow
**Performance Goals**: Benchmark cohort assembly completes in <= 10 minutes for one representative ROI/year; each comparison run emits metrics and recommendation inputs in a single invocation
**Constraints**: Planetary Computer remains the production baseline; no Stage 1 replacement; no canonical schema changes without a separate migration-backed feature; benchmark failures must degrade to logged skips
**Scale/Scope**: One or more representative ROI/year cohorts; one baseline classifier (`rf-v0.1.0`) and one benchmark variant (`alphaearth-benchmark-v0.1.0`)

## Constitution Check

*GATE: Must pass before benchmark implementation begins. Re-check after design finalization.*

Verify ALL of the following before proceeding:

- [x] **Anti-Context Rot (II)**: Checked `AGENTS.md` Sections 4, 5, and 6; no schema names, API URLs, or model versions are inferred.
- [x] **Tech Stack (III)**: Plan stays within the locked stack and treats AlphaEarth only as a benchmark input source.
- [x] **Spatial Integrity (IV)**: No canonical schema changes are required for the initial benchmark spike.
- [x] **API Resilience (V)**: Earth Engine/AlphaEarth failures are handled as logged benchmark skips and must not block production flows.
- [x] **ML Registry (VI)**: The comparison uses the registered baseline `rf-v0.1.0` and the registered benchmark variant `alphaearth-benchmark-v0.1.0`.
- [x] **Foundation-Model Benchmark Gate (VII)**: The plan preserves the Stage 1 NDVI anomaly path and the Planetary Computer production baseline.

*Conclusion: GATE PASSED. Wave 1.5 is constitutionally compliant as a benchmark-only spike.*

## Project Structure

### Documentation (this feature)

```text
specs/003-alphaearth-benchmark/
├── plan.md              # This file
├── spec.md              # Benchmark scope and success criteria
└── tasks.md             # Implementation task list
```

### Source Code (repository root)

```text
app/
├── services/
│   ├── alphaearth_client.py          # Benchmark-only Earth Engine / embedding access wrapper
│   ├── benchmark_dataset.py          # Cohort assembly and split alignment
│   ├── alphaearth_benchmark.py       # Baseline-vs-benchmark evaluation orchestration
│   └── benchmark_report.py           # Recommendation/report generation helpers
├── ml/
│   └── stage2_alphaearth_benchmark.py  # Experimental classifier wrapper for annual embeddings
└── scripts/
    └── run_alphaearth_benchmark.py   # CLI entry point for Wave 1.5 runs

tests/
├── integration/
│   └── test_alphaearth_benchmark_workflow.py
└── unit/
    ├── test_alphaearth_client.py
    ├── test_benchmark_dataset.py
    ├── test_alphaearth_benchmark.py
    └── test_benchmark_report.py

docs/
└── research/
    └── alphaearth-benchmark-report.md  # Optional persisted evidence output
```

**Structure Decision**: Wave 1.5 adds only benchmark-specific services, one experimental Stage 2 classifier wrapper, unit/integration tests, and a report artifact path. It does not add public API routes or modify canonical ORM models in the initial spike.

## Implementation Phases

### Phase 0 — Benchmark Access Validation

- Confirm benchmark-only access assumptions for AlphaEarth annual embeddings.
- Define one representative ROI/year cohort and coverage-check workflow.
- Ensure failures are surfaced as logged skips rather than fatal errors.

### Phase 1 — Matched Cohort Assembly

- Build a benchmark cohort definition from existing ROI, observation, and split inputs.
- Align AlphaEarth embedding samples to the same labeled observations used by the baseline Stage 2 classifier.
- Preserve reproducible train/test splits across baseline and benchmark variants.

### Phase 2 — Baseline vs Benchmark Evaluation

- Wrap the experimental Stage 2 benchmark variant around annual 64D embeddings.
- Evaluate `rf-v0.1.0` and `alphaearth-benchmark-v0.1.0` on identical cohorts.
- Record precision, recall, F1, runtime, dependency burden, auth complexity, and coverage findings.

### Phase 3 — Recommendation Recording

- Generate a report artifact summarizing benchmark results and operational findings.
- Emit an explicit go/no-go recommendation.
- Confirm the production roadmap remains unchanged unless a future amendment is proposed from evidence.

## Risk Management

| Risk | Mitigation |
| :--- | :--- |
| AlphaEarth access is unavailable or quota-limited | Treat access failures as logged benchmark skips and keep Wave 1 / Wave 2 unblocked |
| Comparison is scientifically invalid due to mismatched splits | Encode one cohort definition reused by baseline and benchmark runs |
| Benchmark enthusiasm leaks into production architecture | Keep all work under Wave 1.5 benchmark scope with no production route/schema replacement |
| Annual embeddings do not fit Stage 1 temporal logic | Explicitly prohibit Stage 1 replacement in code, spec, and constitution |
| Evidence is lost in chat history | Persist metrics and recommendation inputs in a repository artifact or docs/research output |

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :-------- | :--------- | :---------------------------------- |
| None | N/A | N/A |
