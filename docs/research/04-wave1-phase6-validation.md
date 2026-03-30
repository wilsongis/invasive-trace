# Wave 1 Phase 6 Validation Evidence

Date: 2026-03-27
Branch: 004-wave1-spatial-infrastructure-seeding

## Command Runs

- `just db-migrate`: PASS
- `just seed-data`: PASS
  - Observed result: `inserted=0`, `skipped=200`, `inat_retries=0`, `eddmaps_retries=0`
  - EDDMapS returned HTTP 404 and was logged/skipped without crashing.
- `just seed-data-dry-run`: PASS
  - Observed result: `inserted=0`, `skipped=200`, `inat_retries=0`, `eddmaps_retries=0`
- `just verify`: PASS
  - Ruff checks passed
  - Pytest passed: 23 tests

## SC-004 Retry Evidence (HTTP 429)

- During live Phase 6 validation command runs, no HTTP 429 events were observed.
- Retry schedule behavior is covered by deterministic unit tests:
  - `tests/unit/test_inat_consumer.py`
  - `tests/unit/test_eddmaps_consumer.py`
- Those tests verify exponential backoff with seeded jitter and explicit sleep schedule assertions.

## Checkpoint Criteria

- Canonical tables exist and migration is healthy (`just db-migrate` PASS).
- Observation seeding path executes without crashes (`just seed-data` PASS).
- ROI create/list/fetch behavior remains validated by integration tests in `just verify`.

## Notes

- `just research-sync` preflight requires interactive Google authentication; automated completion is blocked until manual sign-in is performed in the browser prompt.
