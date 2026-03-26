<!--
Sync Impact Report:
- Version change: 0.0.0 -> 1.0.0
- List of modified principles:
  - PRINCIPLE_1_NAME -> I. Research-First Protocol
  - PRINCIPLE_2_NAME -> II. The Agent Memory Protocol
  - PRINCIPLE_3_NAME -> III. Global Tech Stack (NON-NEGOTIABLE)
  - PRINCIPLE_4_NAME -> IV. Universal Command Bridge
  - PRINCIPLE_5_NAME -> V. Containerized Environment
- Added sections: Genesis Constitution, Core Principles, Additional Constraints, Development Workflow, Governance
- Removed sections: N/A
- Templates requiring updates: N/A (✅ updated / ⚠ pending)
- Follow-up TODOs: N/A
-->
# Genesis Constitution

## Core Principles

### I. Research-First Protocol
Every piece of feature code must be grounded in the documents found in `/docs/research/` or the linked NotebookLM. Experimental features must use the Dev notebook (`just research-sync`). Only sync to Prod when the Software Requirements Specification (SRS) is finalized.

### II. The Agent Memory Protocol
Read-Execute-Write protocol strictly enforced. Always read `AGENTS.md` before starting a task to gain context. Work step-by-step. Update `AGENTS.md` with the current status and new knowledge before ending the task.

### III. Global Tech Stack (NON-NEGOTIABLE)
Backend must be FastAPI (Python 3.12 managed by UV). Frontend must be Jinja2 + HTMX + Tailwind. Automation MUST use Just + UV. MCP Tools must use NotebookLM-MCP. Do not deviate from these technologies unless explicitly authorized.

### IV. Universal Command Bridge
Do not use raw shell commands for standard tasks. Use the `just` command bridge to ensure cross-platform (Mac/Windows) stability (e.g., `just start`, `just run`, `just lint`, `just research-sync`).

### V. Containerized Environment
The primary environment is containerized via `Containerfile`. Database relies on PostGIS with spatial extensions. Ensure all database interactions assume the PostGIS context.

## Additional Constraints

All project state, architectural decisions, and session memory are stored in `AGENTS.md`. `AGENTS.md` is the single source of truth. Code formatting must pass Ruff standards (`just lint`).

## Development Workflow

1. **READ**: Read `AGENTS.md` for context.
2. **SYNC**: Sync knowledge with NotebookLM using `just research-sync`.
3. **PLAN**: Create/update the executable specification based on research.
4. **EXECUTE**: Implement changes according to the Global Tech Stack.
5. **VERIFY**: Run `just lint` to enforce formatting.
6. **WRITE**: Update `AGENTS.md` with new project state before concluding.

## Governance

This Constitution and the `AGENTS.md` file supersede all other practices. Any architectural changes must be updated in `AGENTS.md` first. All PRs and reviews must verify compliance with the Global Tech Stack and Research-First Protocol. 

**Version**: 1.0.0 | **Ratified**: 2026-03-06 | **Last Amended**: 2026-03-06
