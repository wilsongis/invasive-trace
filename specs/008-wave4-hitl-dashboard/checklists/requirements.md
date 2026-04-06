# Requirements Checklist: Wave 4 — HITL Dashboard

## Specification Completeness

- [x] Feature overview and goals are defined.
- [x] User scenarios cover all three priority levels (P1, P2, P3).
- [x] Each user story has independent test criteria and acceptance scenarios.
- [x] Edge cases are documented (invalid UUID, missing fields, concurrent writes, empty state, HTMX errors).
- [x] Functional requirements (FR-001 through FR-015) are specific and testable.
- [x] Non-functional constraints (NFR-001 through NFR-007) reference the mandated stack and schema contracts.
- [x] Key entities are identified with no new tables required.
- [x] Architecture data flow diagram is included.
- [x] Out-of-scope items are explicitly listed.

## Plan Completeness

- [x] Technical context references the locked stack without deviation.
- [x] Constitution Check is present with all six gates listed.
- [x] Project structure maps all new and modified files.
- [x] Implementation phases (4A, 4B, 4C, 6) have clear goals, files, tasks, and exit criteria.
- [x] No schema migration is required.

## Task Completeness

- [x] Tasks are numbered sequentially (W4-T001 through W4-T014).
- [x] Each task references exact file paths.
- [x] Phase dependencies are documented.
- [x] Parallel opportunities are identified.
- [x] Completion criteria are specific and verifiable.

## Data Model Completeness

- [x] Existing table columns are documented with Wave 4 update semantics.
- [x] New Pydantic schemas (ValidationRequest, ValidationResponse) are defined with field-level validation rules.
- [x] Example request and response bodies are provided.
- [x] Retraining trigger query is documented.
- [x] HTMX partial contract for prediction_card.html specifies required visual elements and HTMX attributes.

## Cross-Document Consistency

- [x] `spec.md` FR-001 through FR-015 map to tasks in `tasks.md`.
- [x] `plan.md` phases map to task groupings in `tasks.md`.
- [x] `data-model.md` schemas match the request/response contracts in `spec.md`.
- [x] `AGENTS.md` Section 4 schema is referenced verbatim (no column changes).
- [x] `TODO.md` Wave 4 section (W4-T001 through W4-T010) is consistent with `tasks.md` (W4-T001 through W4-T014 — expanded with setup, polish, and AGENTS.md update tasks).
- [x] Retraining threshold of 50 is consistent across all documents.

## Constitution Compliance (`.specify/memory/constitution.md`)

- [x] **Principle I (Research-First)**: W4-T001 research preflight task included; no remote-sensing decisions in Wave 4.
- [x] **Principle II (Anti-Context Rot)**: `plan.md` Constitution Check references AGENTS.md Sections 4, 5, 6; no guessed column names, URLs, or model versions.
- [x] **Principle III (Tech Stack)**: FastAPI, Jinja2, HTMX, Tailwind CSS, async SQLAlchemy, Ruff, uv, just — no prohibited technologies.
- [x] **Principle IV (Spatial Integrity)**: No migration; writes only to existing `validated` and `validator_notes` columns; tri-state semantics preserved.
- [x] **Principle V (Resilient APIs)**: No external API calls in Wave 4; HTMX error fallbacks specified.
- [x] **Principle VI (ML Registry)**: No model version changes; retraining trigger at ≥ 50 reviewed rows.
- [x] **Principle VII (Benchmark Gate)**: No foundation-model or embedding references.
- [x] **API Versioning**: All endpoints under `/api/v1/`; `GET /` is the dashboard root (permitted operational exception).
- [x] **`just verify` gate**: W4-T013 in `tasks.md`.
