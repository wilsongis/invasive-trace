# Quickstart Guide: Project Genesis

Welcome to your new project spawned from the Genesis template. This guide will get you running in under 5 minutes.

## 1. Environment Setup

Ensure you have install requirements:
- Python 3.12+ (managed by `uv`)
- `just` command runner
- Podman (or Docker)

## 2. Initializing the Project

From the root of your newly cloned repository, run:

```bash
# Sets up your virtual environment, fetches dependencies, and readies the template
just init
```

## 3. Initializing AI Agents

Project Genesis uses Spec-Driven Development. Initialize your chosen agent(s):

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# Replace 'copilot' with 'claude', 'opencode', or 'gemini' as needed.
specify init . --here --ai copilot --script sh
```

Make sure you update `AGENTS.md` with your specific NotebookLM ID if you are using the NotebookLM MCP.

## 4. Running the Application

You have two choices for running the app locally:

**Native (Fastest for UI/API development):**
```bash
just run
```
*Note: This runs the application natively on your host machine via UV. You will need a local Postgres instance running if your app requires the DB.*

**Containerized (Full Environment with PostGIS):**
```bash
just start
```
*Note: This builds and spins up the full Podman stack, including the PostGIS database.*

## 5. Development Workflow

Never make random code changes. Follow the Spec-Driven workflow using your AI agent:

1. `/speckit.specify [feature]`
2. `/speckit.plan`
3. `/speckit.tasks`
4. `/speckit.implement`

Run `just lint` before any commit to ensure your code matches the template formatting guidelines.
