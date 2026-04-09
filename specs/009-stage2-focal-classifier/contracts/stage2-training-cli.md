# Contract: Stage 2 Training CLI

## Command

uv run python -m app.scripts.train_classifier

## Scope

Defines expected behavior for training and publishing the Stage 2 classifier artifact.

## Inputs

- Database rows from:
  - spectral_time_series (feature source)
  - ground_truth_observations (label source)
- Environment configuration from existing app settings.

## Output Artifact

- Path: models/FocalClassifier/rf-v0.1.0/classifier.pkl
- Format: joblib serialized scikit-learn RandomForest model

## Success Behavior

1. Script exits with code 0 when training succeeds.
2. Artifact is written to canonical model path.
3. Logs include sample count and class count used for fit.

## Data Quality Rules

1. Training candidates must be deterministic for the same input dataset.
2. Masked or invalid spectral rows are excluded from cohort build.
3. Labels must come from confirmed observation records.

## Fallback Behavior

In local/dev situations with insufficient real data, script may generate a synthetic artifact only when explicitly documented in logs. This path is for developer continuity and must not be treated as production-grade model evidence.

## Failure Behavior

Script exits non-zero when:
- model cannot be fit due to invalid candidate set after filtering,
- artifact cannot be written,
- required runtime dependencies are unavailable.

## Compatibility

- Keeps model version pinned to rf-v0.1.0.
- Consumed directly by app.ml.stage2_classifier load path.
