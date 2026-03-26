# Tasks: 001-genesis-srs

**Input**: Design documents from `/specs/001-genesis-srs/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Initialize Python project via UV (`just init` scaffolding) in `/Users/wilsonm/Development/genesis/`
- [ ] T002 Configure Ruff for codebase formatting and linting in `pyproject.toml`
- [ ] T003 Implement Universal Command Bridge by defining standard targets (`start`, `run`, `lint`, `research-sync`) in `justfile`
- [ ] T004 Setup Podman container structure in `Containerfile`

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [ ] T005 [P] Setup PostGIS database scaffolding and connection logic in `src/core/database.py`
- [ ] T006 [P] Setup FastAPI application routing and middleware in `src/main.py`
- [ ] T007 Initialize base SQLAlchemy Spatial model in `src/models/base.py`
- [ ] T008 Configure `.specify` memory and link `AGENTS.md` Constitution rules in `.specify/memory/constitution.md`

## Phase 3: User Story 1 - Project Initialization and Setup (Priority: P1)

**Goal**: A developer clones the Genesis template for a new application.
**Independent Test**: Can fully initialize the application via CLI commands and see a running instance.

### Implementation for User Story 1

- [ ] T009 [US1] Finalize `templates/AGENTS.md.template` for base agent scaffolding
- [ ] T010 [US1] Create basic HTML shell using Jinja2 in `src/templates/base.html`
- [ ] T011 [US1] Configure Tailwind CSS utility classes linked to HTMX in `src/static/styles.css`

## Phase 4: User Story 2 - Spec-Driven Feature Development (Priority: P2)

**Goal**: An AI Agent is tasked with building a new feature adhering to the Spec-Driven workflow.
**Independent Test**: The agent memory protocol correctly directs them to read constraints before generating code.

### Implementation for User Story 2

- [ ] T012 [P] [US2] Document the Spec-Driven workflow steps in `docs/getting_started.md`
- [ ] T013 [P] [US2] Update `AGENTS.md` to map strict technical stack requirements (FastAPI, HTMX, Tailwind) for agents to follow

## Phase 5: User Story 3 - Application Runtime (Priority: P3)

**Goal**: An End User interacts with the deployed web application.
**Independent Test**: The application returns expected dynamic HTMX fragments under 200ms.

### Implementation for User Story 3

- [ ] T014 [US3] Build a sample robust HTTP endpoint returning Jinja2 HTMX fragments in `src/api/demo.py`
- [ ] T015 [US3] Ensure PostGIS connectivity is operational on the demo endpoint

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T016 Run `just verify` (linting and test suites) to enforce compliance
- [ ] T017 Finalize `.gitignore` rules to protect `.specify/` templates while ignoring agent-specific logs
