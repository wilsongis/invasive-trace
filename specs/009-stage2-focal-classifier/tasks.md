# Tasks: Stage 2 Focal Classifier and Feature Extraction

**Feature**: `specs/009-stage2-focal-classifier/`
**Branch**: `009-stage2-focal-classifier`
**Generated**: 2026-04-08
**Input**: spec.md, plan.md, research.md, data-model.md, quickstart.md, contracts/

---

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no shared dependency on incomplete tasks)
- **[Story]**: Phase 3+ user story label ([US1], [US2], [US3])
- Setup / Foundational / Polish phases carry no story label
- Exact file paths included in all task descriptions

---

## Dependencies & Execution Order

```
Phase 1: Setup (no dependencies)
    ↓
Phase 2: Foundational (depends on Phase 1)
    ↓
Phase 3: [US1] Produce Predictions  ← MVP
    ↓
Phase 4: [US2] Resilient Operation  (depends on Phase 2 + Phase 3)
    ↓
Phase 5: [US3] Auditability         (depends on Phase 2 + Phase 3)
    ↓
Phase 6: Polish & Cross-Cutting
```

### Parallel Opportunities per Phase
- **Phase 2**: T007–T011 are all different files (feature extractor, classifier, backoff utility)
- **Phase 3**: T015–T021 are independent implementation units; tests run in parallel once target is complete
- **Phase 4**: T022–T028 all operate on separate concerns (error handling, retry, summary)
- **Phase 5**: T029–T035 are all independent determinism/logging concerns

### MVP Scope
**Minimum Viable Delivery**: Phase 1 + Phase 2 + Phase 3 = **21 tasks**
- Produces: working training → inference → DB-persist pipeline for US1
- Enables: Stage 3 U-Net can begin; HITL dashboard has Stage 2 outputs to review

---

## Phase 1: Setup & Compliance Gates

**Goal**: Verify directory structure, file scaffolds, and quality gate compliance.

### Independent Test Criteria
- [ ] All source directories exist: `app/ml/`, `app/services/`, `app/scripts/`, `tests/unit/`, `tests/integration/`, `models/FocalClassifier/rf-v0.1.0/`
- [ ] All required module files present: `app/ml/stage2_classifier.py`, `app/services/feature_extractor.py`, `app/scripts/train_classifier.py`, `app/scripts/run_stage2_inference.py`
- [ ] All test scaffolds present: `tests/unit/test_stage2_classifier.py`, `tests/unit/test_feature_extractor.py`, `tests/integration/test_stage2_pipeline.py`
- [ ] `just verify` passes with zero errors (ruff lint + pytest)

---

  - [X] T001 Verify directory structure exists; create any missing dirs: `app/ml/`, `app/services/`, `app/scripts/`, `tests/unit/`, `tests/integration/`, `models/FocalClassifier/rf-v0.1.0/`

  - [X] T002 [P] Verify source module files present (create stubs if missing): `app/ml/stage2_classifier.py`, `app/services/feature_extractor.py`, `app/scripts/train_classifier.py`, `app/scripts/run_stage2_inference.py`

  - [X] T003 [P] Verify test files present (create stubs if missing): `tests/unit/test_stage2_classifier.py`, `tests/unit/test_feature_extractor.py`, `tests/integration/test_stage2_pipeline.py`

  - [X] T004 Review AGENTS.md Sections 4, 5, 6 for anti-context-rot compliance — confirm no hardcoded schema names, API URLs, or model version strings in source files

  - [ ] T005 [P] Run research preflight: `just research-sync` then `just research-test` to validate NotebookLM MCP connection is live

  - [X] T006 Run `just lint` (ruff check + format) — must pass with zero errors before any implementation begins

---

## Phase 2: Foundational — Feature Extraction & Model Infrastructure

**Goal**: Implement the shared feature extraction pipeline, model loading utilities, and retry infrastructure that all three user stories depend on. No implementation of training or inference business logic here.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Independent Test Criteria
- [ ] `FeatureExtractor` class instantiates and exposes required method signatures
- [ ] `extract_training_cohort()` joins `ground_truth_observations` + `spectral_time_series`, returns 12-feature vectors
- [ ] `generate_candidates()` returns deterministic centroid + 500m grid for a given ROI
- [ ] `load_classifier()` reads `classifier.pkl` from `models/FocalClassifier/{version}/`
- [ ] `clip_confidence()` clamps any float to [0.0, 1.0]
- [ ] `retry_with_backoff()` retries up to 3 times with jitter, returns None on exhaustion

---

  - [X] T007 Implement `FeatureExtractor` class in `app/services/feature_extractor.py`:
  - `extract_training_cohort(roi_ids: list[UUID]) -> list[TrainingCohortRecord]` — deterministic cohort query joining `ground_truth_observations` (is_confirmed=TRUE) with `spectral_time_series` (is_masked=FALSE) via 3-month temporal window (±45 days); returns rows ordered by (roi_id, observation_date, species_label)
  - `extract_inference_vector(roi_id: UUID, candidate_geom: Point) -> InferenceVector` — full time series aggregates (no window); 12-element vector (NDVI/ENDVI/Red-Edge × min/max/mean/std)
  - `generate_candidates(roi_id: UUID) -> list[CandidateLocation]` — ROI centroid via ST_Centroid + deterministic 0.0045° grid filtered by ST_Intersects; sorted by grid_index

  - [X] T008 [P] Implement model loading utilities in `app/ml/stage2_classifier.py`:
  - `load_classifier(version: str) -> RandomForestClassifier` — joblib.load from `./models/FocalClassifier/{version}/classifier.pkl`; raise FileNotFoundError with clear message if missing
  - `get_model_metadata(version: str) -> dict` — load `metadata.json`; validate presence of `feature_names`, `class_labels`, `model_version` keys
  - `clip_confidence(confidence: float) -> float` — `max(0.0, min(1.0, confidence))`

  - [X] T009 [P] Implement exponential backoff utility in `app/services/feature_extractor.py` (or extract to `app/services/resilience.py` if reuse warrants it):
  - `retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0) -> Any | None`
  - Delay formula: `base_delay × 2^attempt + uniform_random_jitter(0, 0.5)`
  - Log each retry attempt at WARNING level; log final exhaustion at ERROR level
  - Return None on exhaustion (never raise); caller responsible for skip logic

  - [X] T010 [P] Unit tests for foundational utilities in `tests/unit/test_feature_extractor.py`:
  - `test_clip_confidence_lower_bound()` — `clip_confidence(-0.5)` returns `0.0`
  - `test_clip_confidence_upper_bound()` — `clip_confidence(1.5)` returns `1.0`
  - `test_clip_confidence_passthrough()` — `clip_confidence(0.75)` returns `0.75`
  - `test_retry_success_on_third_attempt()` — func fails twice, succeeds on third; returns result
  - `test_retry_exhaustion_returns_none()` — func fails 3 times; returns None, no exception raised
  - `test_retry_jitter_varies_delays()` — consecutive retry delays are not identical

  - [X] T011 [P] Unit tests for model loading in `tests/unit/test_stage2_classifier.py`:
  - `test_load_classifier_success()` — loads a synthetic joblib artifact; has `predict` and `predict_proba` attributes
  - `test_load_classifier_missing_version()` — raises FileNotFoundError (not a generic exception) when artifact path absent
  - `test_get_model_metadata_keys()` — metadata dict contains `feature_names`, `class_labels`, `model_version`

**Checkpoint**: Foundation ready — user story phases can now begin.

---

## Phase 3: [US1] Produce Species Predictions from ROI Inputs (Priority: P1) 🎯 MVP

**Goal**: Implement the complete training and inference pipeline that transforms ROI spectral history + confirmed observations into species-level predictions persisted to `invasion_predictions`.

**Independent Test**: Run training with a seeded test ROI, then run inference — verify predictions exist in DB with `species_label`, `confidence ∈ [0.0, 1.0]`, `model_version = 'rf-v0.1.0'`, and valid geometry.

---

  - [X] T012 [P] [US1] Fix pre-existing `pipeline.py` Stage 2 bug in `app/services/pipeline.py`:
  - Line ~147: `stage2.predict(feature_vec)` crashes because `feature_vec` is never assigned in the loop body
  - Fix: add `feature_vec = await build_feature_vector(ndvi=row.ndvi, endvi=row.endvi, red_edge=row.red_edge, lon=lon, lat=lat)` immediately before the `stage2.predict()` call (import `build_feature_vector` already present on line 27)
  - This unblocks `POST /api/v1/rois/{roi_id}/pipeline/run` for any ROI with unmasked spectral data
  - Unit test: `test_pipeline_stage2_feature_vec_built()` — mock `build_feature_vector` + `stage2.predict`; assert both called once per anomaly

  - [X] T013 [P] [US1] Unit tests for training pipeline in `tests/unit/test_stage2_classifier.py`:
  - `test_rf_training_hyperparams()` — fitted classifier has `n_estimators=100`, `max_depth=15`, `min_samples_leaf=5`, `class_weight='balanced'`
  - `test_rf_stratified_split()` — species distribution in train/test sets mirrors input cohort
  - `test_rf_metrics_numeric()` — CV and test F1-macro, precision-macro, recall-macro are floats in [0.0, 1.0]
  - `test_rf_model_serialization()` — `joblib.dump` + `joblib.load` round-trip preserves predict/predict_proba

  - [X] T013 [P] [US1] Unit tests for inference pipeline in `tests/unit/test_stage2_classifier.py`:
  - `test_infer_confidence_clipped()` — any raw predict_proba value > 1.0 or < 0.0 is clipped before returning
  - `test_infer_dry_run_no_db_write()` — `dry_run=True` produces PredictionOutput objects but performs no DB INSERT
  - `test_infer_model_version_set()` — all PredictionOutput records carry `model_version = 'rf-v0.1.0'`

  - [X] T014 [P] [US1] Implement RandomForest training in `app/ml/stage2_classifier.py`:
  - `train_classifier(training_cohort: list[TrainingCohortRecord], output_dir: str, force_retrain: bool = False) -> TrainingResult`
  - Skip if artifact exists and `force_retrain=False`; log and return existing metadata
  - Build feature matrix X (N × 12) and label vector y from cohort using canonical 12-feature order: `[ndvi_min, ndvi_max, ndvi_mean, ndvi_std, endvi_min, endvi_max, endvi_mean, endvi_std, red_edge_min, red_edge_max, red_edge_mean, red_edge_std]`
  - Hyperparameters: `n_estimators=100, max_depth=15, min_samples_leaf=5, class_weight='balanced', random_state=42`
  - 70/30 stratified train/test split (`random_state=42`)
  - 5-fold `StratifiedKFold` CV on train set; compute mean ± std F1-macro
  - Evaluate on test set: F1-macro, precision-macro, recall-macro, balanced accuracy
  - Return `TrainingResult` with all metrics

  - [X] T015 [P] [US1] Implement model artifact persistence in `app/ml/stage2_classifier.py`:
  - `persist_artifacts(result: TrainingResult, output_dir: str) -> None`
  - `{output_dir}/classifier.pkl` — joblib-serialized RandomForestClassifier
  - `{output_dir}/metadata.json` — `model_version`, `training_date` (ISO 8601), `training_roi_ids`, `training_sample_count`, `training_sample_count_by_species`, `feature_names`, `class_labels`, `hyperparameters`, `cv_f1_macro_mean`, `cv_f1_macro_std`, `cv_fold_scores` (list of per-fold F1), `test_f1_macro`, `test_precision_macro`, `test_recall_macro`, `test_balanced_accuracy`
  - `{output_dir}/feature_names.txt` — 12 names, one per line
  - `{output_dir}/class_labels.txt` — target species, one per line
  - `{output_dir}/README.md` — model card: training date, sample counts, test metrics

  - [X] T016 [P] [US1] Implement `train_classifier.py` script in `app/scripts/train_classifier.py`:
  - CLI: `--roi-ids` (optional, comma-separated UUIDs; omit for auto-detect), `--output-dir` (required), `--force-retrain` (flag)
  - Auto-detect ROIs: query all ROIs with ≥10 confirmed `ground_truth_observations` per species
  - Call `FeatureExtractor.extract_training_cohort(roi_ids)` then `stage2_classifier.train_classifier()` then `persist_artifacts()`
  - Print JSON run summary to stdout: `status`, `model_version`, `training_date`, `training_sample_count`, `cv_f1_macro_mean`, `cv_f1_macro_std`, `test_f1_macro`, `test_precision_macro`, `test_recall_macro`, `run_summary` (skip counts)
  - Exit 0 on success, exit 1 on failure

  - [X] T017 [P] [US1] Implement `infer_predictions()` in `app/ml/stage2_classifier.py`:
  - `infer_predictions(roi_ids: list[UUID], model_version: str, dry_run: bool = False, db: AsyncSession) -> InferenceResult`
  - Load classifier via `load_classifier(model_version)`
  - For each roi_id: call `generate_candidates()` → for each CandidateLocation call `extract_inference_vector()` → `classifier.predict()` → `classifier.predict_proba()` → `clip_confidence()`
  - Build `InvasionPrediction` ORM record: `species_label`, `confidence` (clipped), `geom` (candidate point, SRID 4326), `roi_id`, `model_version='rf-v0.1.0'`, `validated=None`
  - Batch INSERT via `db.add_all()` + `await db.commit()`; skip if `dry_run=True`
  - Return `InferenceResult` with per-ROI and total counts

  - [X] T018 [P] [US1] Implement `run_stage2_inference.py` script in `app/scripts/run_stage2_inference.py`:
  - CLI: `--roi-ids` (required, comma-separated UUIDs), `--model-version` (required), `--dry-run` (flag)
  - Load classifier metadata, call `infer_predictions()`
  - Print JSON run summary: `status`, `model_version`, `inference_date`, `run_summary.roi_results[]` (per ROI: `roi_id`, `candidates_generated`, `candidates_processed`, `predictions_written`, `skipped_invalid_features`, `inference_time_sec`), `total_predictions_written`, `total_inference_time_sec`
  - Exit 0 on success, exit 1 on failure

  - [X] T019 [P] [US1] Integration test end-to-end in `tests/integration/test_stage2_pipeline.py`:
  - `test_stage2_pipeline_end_to_end()` — seed test ROI + 15 confirmed observations + 60 unmasked spectral rows; run train → verify `classifier.pkl` created and `test_f1_macro` logged; run inference → query `invasion_predictions`; assert:
    - `predictions_written > 0`
    - `predictions_written / candidates_generated >= 0.99` (SC-001: ≥99% of eligible candidates classified)
    - all `confidence` in [0.0, 1.0]
    - all `model_version = 'rf-v0.1.0'`
    - all geom SRID 4326, not null

**Checkpoint**: US1 complete — training + inference pipeline functional and independently testable.

---

## Phase 4: [US2] Operate Resiliently on Imperfect Inputs (Priority: P2)

**Goal**: Layer skip logic, retry policies, and run summaries on top of the Phase 3 pipeline so runs complete at 95%+ rate under partial-data and transient-failure conditions.

**Independent Test**: Inject cloud-masked records, missing scenes, and mock HTTP 429 responses — verify graceful skips, bounded retries, and detailed run summaries with per-reason skip counts.

---

- [ ] T020 [P] [US2] Implement feature-vector validation in `app/services/feature_extractor.py`:
  - Before returning any vector, check all 12 values are finite (`math.isfinite`); skip record if any NaN or infinity
  - Enforce minimum scene count: skip record if `scene_count < 3`
  - Enforce non-NULL spectral indices: skip if any of ndvi/endvi/red_edge aggregates are None
  - For each skip: log at WARNING with reason string (e.g., `"skip: scene_count=2 < 3"`) and accumulate into run-level `skip_reasons` dict

- [ ] T021 [P] [US2] Enforce cloud-mask filter in `app/services/feature_extractor.py`:
  - All queries against `spectral_time_series` MUST include `WHERE is_masked = FALSE`
  - Warn (not error) if contributing scene count drops to 0 for a candidate after masking; skip candidate and log

- [ ] T022 [P] [US2] Wire `retry_with_backoff()` to all external API call sites:
  - `app/services/stac_client.py` — wrap STAC item search and asset fetch
  - `app/services/inat_consumer.py` — wrap observation fetch
  - `app/services/eddmaps_consumer.py` — wrap occurrence fetch
  - HTTP 429 and transient connection errors: retry (max 3); permanent errors (401, 404): skip immediately
  - Never propagate unhandled exception from any external call; always return None and continue

- [ ] T023 [P] [US2] Implement run summary accumulation in `app/scripts/train_classifier.py`:
  - Accumulate during cohort assembly: `total_cohort_candidates`, `skipped_invalid_features`, `skipped_low_scene_count`, `skipped_unknown_species`, `final_training_sample_count`
  - Emit all counts in the JSON run summary output (see T016)

- [ ] T024 [P] [US2] Implement per-ROI run summary accumulation in `app/scripts/run_stage2_inference.py`:
  - Per ROI: `candidates_generated`, `candidates_processed`, `predictions_written`, `skipped_invalid_features`, `skipped_missing_scenes`, `skipped_failed_external`, `inference_time_sec`
  - Total across all ROIs: `total_predictions_written`, `total_inference_time_sec`
  - Emit `roi_results` array in JSON run summary (see T018)

- [ ] T025 [P] [US2] Unit tests for resilience behavior in `tests/unit/test_feature_extractor.py`:
  - `test_skip_record_low_scene_count()` — record with `scene_count=2` is skipped; skip reason logged
  - `test_skip_record_nan_feature()` — record with NaN in any of 12 features is skipped; skip reason logged
  - `test_skip_record_cloud_masked()` — scene with `is_masked=TRUE` excluded from aggregation window

- [ ] T026 [P] [US2] Unit tests for retry behavior in `tests/unit/test_feature_extractor.py`:
  - `test_retry_on_http_429()` — mock returning HTTP 429 twice then success; function returns value on third attempt
  - `test_retry_exhausted_returns_none()` — mock always returning HTTP 429; after 3 retries returns None, no exception

- [ ] T027 [P] [US2] Integration test partial-data resilience in `tests/integration/test_stage2_pipeline.py`:
  - `test_stage2_partial_data_handling()` — seed ROI with 10 valid + 5 cloud-masked + 3 below-threshold records; run training; assert training completes successfully on valid subset; assert `run_summary.skipped_invalid_features` or `skipped_low_scene_count` > 0

**Checkpoint**: US2 complete — pipeline survives imperfect inputs without manual recovery.

---

## Phase 5: [US3] Maintain Auditability and Reproducibility (Priority: P3)

**Goal**: Ensure every Stage 2 run is deterministic and produces auditable metadata that identifies inputs, cohort characteristics, model version, and output summary.

**Independent Test**: Execute identical training + inference twice against the same seed data — verify identical cohort order, identical candidate grid, identical prediction set, and that metadata.json captures full lineage.

---

- [ ] T028 [P] [US3] Enforce deterministic training cohort ordering in `app/services/feature_extractor.py`:
  - SQL query result ordered by `(roi_id, observation_date, species_label)` with explicit `ORDER BY`
  - Add inline comment: `# ORDER BY required for deterministic cohort — do not remove`
  - Verify via unit test: run query twice on same fixture, assert list equality

- [ ] T029 [P] [US3] Enforce deterministic candidate grid generation in `app/services/feature_extractor.py`:
  - Grid points generated using `numpy.arange` with fixed seed (`random_state=0`)
  - Final list sorted by `(grid_row, grid_col)` before return
  - Add inline comment: `# Sort required for deterministic inference — seed=0, do not mutate`

- [ ] T030 [P] [US3] Verify metadata.json serialization correctness in `app/ml/stage2_classifier.py`:
  - Confirm all fields from T015 are serialized with `json.dumps(..., indent=2, default=str)` (handles datetime, UUID, numpy types)
  - Confirm `cv_fold_scores` is a JSON array of per-fold F1 floats (not a numpy array)
  - Unit test: load written metadata.json, assert all required keys present and types correct

- [ ] T031 [P] [US3] Enforce model version constant in `app/ml/stage2_classifier.py`:
  - `MODEL_VERSION = "rf-v0.1.0"` as module-level constant (single source of truth)
  - All writes to `invasion_predictions.model_version` use `MODEL_VERSION`; no string literals elsewhere
  - All reads via `load_classifier()` resolve path from `MODEL_VERSION`

- [ ] T032 [P] [US3] Implement structured run logging in `app/scripts/train_classifier.py` and `app/scripts/run_stage2_inference.py`:
  - Python `logging` module; logger name = `invasive_trace.stage2`
  - INFO: run start, run end, input parameters, summary statistics
  - WARNING: each skipped record (with reason)
  - ERROR: each failed external call and any non-fatal exception
  - Log format: `%(asctime)s %(levelname)s %(name)s %(message)s` (container-friendly)

- [ ] T033 [P] [US3] Unit tests for determinism in `tests/unit/test_feature_extractor.py`:
  - `test_training_cohort_order_deterministic()` — two calls against same in-memory fixture yield `==` lists
  - `test_candidate_grid_order_deterministic()` — two calls for same ROI geometry yield `==` candidate lists
  - `test_model_version_constant_used()` — `infer_predictions()` result records all carry `MODEL_VERSION` value

- [ ] T034 [P] [US3] Integration test full audit trail in `tests/integration/test_stage2_pipeline.py`:
  - `test_stage2_audit_trail()` — run training twice; assert `metadata.json` training_sample_count identical; assert `cv_fold_scores` identical; run inference twice; query `invasion_predictions`; assert same prediction count, same species labels, same confidence values (±1e-9 float tolerance)

**Checkpoint**: US3 complete — all three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Validate quality gates, confirm performance budgets, and finalize documentation.

### Independent Test Criteria
- [ ] `just verify` passes: ruff lint + pytest, zero errors
- [ ] Unit + integration test pass rate: 100%
- [ ] Performance: training < 60s per 1000 training samples; inference < 2s per 500 candidates per ROI
- [ ] `models/FocalClassifier/rf-v0.1.0/` directory contains: `classifier.pkl`, `metadata.json`, `feature_names.txt`, `class_labels.txt`, `README.md`

---

  - [X] T035 Run `just lint` (ruff check + format) until zero errors across `app/ml/`, `app/services/`, `app/scripts/`, `tests/`

  - [X] T036 [P] Run `just test` and confirm 100% test pass rate; identify and fix any flaky test isolation issues

- [ ] T037 [P] Validate `models/FocalClassifier/rf-v0.1.0/` artifact directory: confirm all 5 expected files present and metadata.json is valid JSON with required fields

- [ ] T038 [P] Validate Alembic migration state: confirm no new schema changes introduced (expected none per research.md Decision 8); document result; if schema drift found, create and apply migration via `just db-migrate`

- [ ] T039 [P] Performance validation:
  - Time `train_classifier.py` against a 1000-sample synthetic cohort; assert < 60s
  - Time `run_stage2_inference.py` against a 500-candidate ROI; assert < 2s (research.md Decision 11)
  - Log results; note any bottleneck for follow-up

- [ ] T040 [P] Validate quickstart.md Workflow A (training) and Workflow B (inference) end-to-end with local environment; update any stale command examples

  - [X] T041 Run `just verify` (ruff + pytest combined gate) — must show 0 lint errors, all tests green; record result in AGENTS.md

- [ ] T042 Update AGENTS.md Section 9 (Active Context & Roadmap): mark Stage 2 Focal Classifier implementation complete; record quality gate result; update `⏱️ State` line

---

## Test Matrix by User Story

| Test Type | [US1] Predictions | [US2] Resilience | [US3] Auditability |
|-----------|------------------|------------------|--------------------|
| Unit | T012, T013 | T025, T026 | T033 |
| Integration | T019 | T027 | T034 |
| Infrastructure | T010, T011 | — | — |

---

## Risk Mitigation

| Risk | Mitigation Task |
|------|-----------------|
| Feature vector wrong shape or non-finite values | T010, T020 |
| Confidence outside [0.0, 1.0] reaches DB | T013 (unit), T017 (clip_confidence call site) |
| Model artifact missing at inference time | T011 (FileNotFoundError test) |
| Cloud-masked scenes silently included in features | T021 (filter enforcement) |
| Non-deterministic cohort breaks reproducibility | T028, T033 |
| External API failure aborts full run | T022, T026 |
| Performance budget exceeded (>2s per ROI) | T039 |

---

## Task Count Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Phase 1 — Setup | T001–T006 | — |
| Phase 2 — Foundational | T007–T011 | — |
| Phase 3 — US1 Predictions | T012–T019 | [US1] |
| Phase 4 — US2 Resilience | T020–T027 | [US2] |
| Phase 5 — US3 Auditability | T028–T034 | [US3] |
| Phase 6 — Polish | T035–T042 | — |

**Total: 42 tasks**

**MVP Scope (US1 only)**: Phase 1 + Phase 2 + Phase 3 = **19 tasks**

---

## Dependency Notes

- **Blocking chain**: T001–T006 → T007–T011 → T012–T019 (US1) → T020–T027 (US2) → T028–T034 (US3) → T035–T042
- **Parallel within Phase 2**: T007, T008, T009 are different files — can run concurrently
- **Parallel within Phase 3**: T012–T013 (tests) and T014–T018 (impl) can parallelize; integration test T019 requires T014–T018 complete
- **Skip-ahead path (MVP fast track)**: Complete T001–T019 → jump directly to T035–T042; defer US2/US3 to next sprint

