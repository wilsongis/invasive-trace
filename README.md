# 🧬 Project Genesis
This is the baseline template repository for building AI-augmented, Spec-Driven applications using a strictly enforced Python+FastAPI+HTMX+PostGIS stack.
## 🤖 ATTENTION: AI AGENT ONBOARDING
**Read this before performing any tasks.** You are operating as the **Legacy Mentor**. This repository is governed by the **Agent Memory Protocol (v1.0)**.

### 1. Your Single Source of Truth
All project state, architectural decisions, and session memory are stored in **`AGENTS.md`** and enforced by the **`.specify/memory/constitution.md`**.
- **Requirement:** At the start of every session, you must read `AGENTS.md` and the Spec Kit constitution.
- **Requirement:** Before concluding, you must update `AGENTS.md` with the new project state.

### 2. The Command Bridge (Universal)
Do not use raw shell commands. Use `just` to ensure cross-platform (Mac/Windows) stability.

| Task | Command | AI Tooling Note |
| :--- | :--- | :--- |
| **Initialize** | `just init` | Sets up venv and template files. |
| **Research Sync** | `just research-sync` | Ingests `/docs/research` into NotebookLM. |
| **Research Auth** | `just research-auth` | Logs into AntiGravity/NotebookLM MCP. |
| **Start Server** | `just start` | Manages Podman container lifecycle. |
| **Native Run** | `just run` | Runs FastAPI via `uv` (Native). |
| **Standards** | `just lint` | Enforces Ruff formatting. |

### 3. Spec-Driven & Research-First Protocol
This is a research-heavy project leveraging Spec-Driven Development via GitHub Spec Kit. You are prohibited from writing feature code unless it is planned and specified.
- **Step 1 (Research):** Use `notebooklm-mcp` to query the project's knowledge base.
- **Step 2 (Specify):** Use `/speckit.specify [feature]` to define the requirement.
- **Step 3 (Plan):** Use `/speckit.plan` to generate the technical implementation plan.
- **Step 4 (Tasks):** Use `/speckit.tasks` to break the plan into actionable checklist steps.
- **Step 5 (Implement):** Use `/speckit.implement` to execute the code.

### 4. Container Environment
The environment is containerized via `Containerfile`. 
- **Tech Stack:** FastAPI, PostGIS, Python 3.12 (UV managed).
- **Access:** The server runs on port `8000`.
- **Database:** PostGIS spatial extensions are pre-configured.

### 5. Memory Recovery
If you lose context or the user says **"Status"**, execute:
1. `cat AGENTS.md`
2. `ls docs/research`
3. Summarize the next steps from the `## Active Context` section of `AGENTS.md`.

---
**Legacy Standard Enforced.**
"Take a deep breath and work on this problem step by step."

## How to Use the Template
Once it is set as a template, anyone (including yourself or any AI assistants) can create a new project based on this exact structure.

There are two ways to use it:

1. Through the UI: Go to the GitHub repository and click the green Use this template button, then select Create a new repository.
2. Through the CLI: You can use the GitHub CLI to clone it directly:

```bash
gh repo create <new-repo-name> --template wilsongis/genesis-template
```

**After cloning**, refer to `docs/getting_started.md` for full instructions on configuring your AI agents and bootstrapping the Spec Kit environment.