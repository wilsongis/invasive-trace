# Research & Technical Decisions: 001-genesis-srs

This document consolidates the technical decisions required to execute the baseline SRS while adhering to the Genesis Constitution constraints.

## 1. Web Framework Architecture
- **Decision:** Use FastAPI for backend routing and Jinja2 strings/templates for frontend rendering.
- **Rationale:** The Constitution requires Python, FastAPI, and HTMX. FastAPI provides rapid async routing and excellent data validation (Pydantic), while returning Jinja2 HTML fragments satisfies the HTMX requirement without needing a heavy JS framework (like React or Vue).
- **Alternatives considered:** Django (rejected: too heavy for the outlined constraints), Flask (rejected: lacks the async and typing benefits of FastAPI).

## 2. Agent Memory and Tooling
- **Decision:** Mandate the use of GitHub Spec Kit (`specify-cli`) and `AGENTS.md`.
- **Rationale:** As identified in the "Evaluating Spec-Driven Development" task, Spec Kit maps perfectly to the Genesis requirement for an executable SR. It allows AI agents to act autonomously while strictly adhering to the project's non-negotiable tech stack defined in `.specify/memory/constitution.md`.
- **Alternatives considered:** Using unstructured markdown prompts (rejected: leads to drift and inconsistent agent behavior across sessions).

## 3. Deployment and Local Environment
- **Decision:** Use Podman and `just`.
- **Rationale:** `just` is explicitly mandated by the Universal Command Bridge principle for cross-platform compatibility (macOS/Windows). Podman is mandated to provide the isolated PostGIS database environment required for future spatial capability.
- **Alternatives considered:** Raw Makefiles (rejected: poor Windows support), direct script execution (rejected: violates Universal Command Bridge doctrine).
