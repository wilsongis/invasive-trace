# Contract: Stage 2 Pipeline API Behavior

## Endpoint

POST /api/v1/rois/{roi_id}/pipeline/run

## Scope

This contract defines Stage 2-observable behavior exposed through the existing Wave 3 pipeline endpoint. It does not add a new API route.

## Request

- Path parameter: roi_id (UUID)
- Body: none

## Response (200)

Content type: application/json

Fields:
- roi_id: UUID
- predictions_created: integer >= 0
- model_version: string
- message: string

Stage 2 requirements:
- model_version must equal rf-v0.1.0.
- predictions_created reflects rows successfully persisted to invasion_predictions.
- message must describe zero-result and partial-result outcomes deterministically.

## Response (404)

Returned when ROI does not exist.

## Behavioral Guarantees

1. Stage 2 classifier output is persisted only with confidence in [0.0, 1.0].
2. Invalid per-candidate inputs are skipped with logging; they do not abort the whole run.
3. Partial external enrichment failures (for example elevation lookup) do not fail the full request.
4. New prediction rows preserve canonical defaults: validated=null and validator_notes=null.

## Compatibility

- Backward compatible with existing Wave 3 endpoint surface.
- No schema changes required.
