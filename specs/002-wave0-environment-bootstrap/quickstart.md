# Quickstart: Wave 0 - Environment Bootstrap

## Prerequisites

- Podman installed and available on PATH
- `just` installed
- `uv` installed
- `.env` created from `.env.example`

## Validation Flow

1. Start the local services:

```bash
just start
```

Expected result:

- PostGIS container becomes healthy
- app container starts cleanly

1. Apply the migration baseline:

```bash
just db-migrate
```

Expected result:

- Alembic connects using the environment-provided `DATABASE_URL`
- baseline migration completes without manual edits

1. Run quality gates:

```bash
just verify
```

Expected result:

- 0 lint errors
- 0 test failures

If `just verify` fails, run diagnostics:

```bash
just lint
just test
```

1. Verify research grounding:

```bash
just research-sync
just research-test
just research-open
```

Expected result:

- MCP connection initializes to `gaia-atlas`
- verification succeeds
- `/docs/research/` is uploaded manually through the NotebookLM UI

## Completion Standard

Wave 0 is complete only when:

- `/healthz` responds successfully
- the DB smoke test passes
- `just verify` is green (with diagnostic lint/test runs if needed)
- NotebookLM grounding is verified and research sources are uploaded
- SC-004 evidence is logged in `specs/002-wave0-environment-bootstrap/checklists/requirements.md`
