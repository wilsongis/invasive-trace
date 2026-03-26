# Getting Started with Project Genesis

Project Genesis uses a **Spec-Driven Development** approach powered by GitHub's Spec Kit. The project enforces strict adherence to a primary Constitution via a multi-agent framework. Follow these steps to set up your environment and use the template effectively.

## 1. Environment Prerequisites

Before initializing the AI agents, ensure you have the following installed on your system:
- **Python 3.12+** (Managed via [`uv`](https://github.com/astral-sh/uv))
- **[Just](https://github.com/casey/just)* (Command runner)
- **Podman/Docker** (For the containerized environment & PostGIS)
- **Git**

## 2. Install Specify CLI

Spec-Driven Development requires the `specify-cli`. Install it globally using `uv`:

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
```

## 3. Configure Your Project

Once your repository is cloned from the Genesis template, you must initialize the Specify environment and configure your preferred AI agents. 

Run the initialization commands for the agents you intend to use. Specify CLI will create the `.specify/` core configuration and link the specific command files for your agents.

```bash
# Initialize for Antigravity (Gemini)
specify init . --ai gemini

# Initialize for GitHub Copilot / VSCode
specify init . --here --ai copilot --script sh

# Initialize for Claude Code
specify init . --here --ai claude --script sh

# Initialize for OpenCode
specify init . --here --ai opencode --script sh
```

*(Note: The `--force` flag can be used if prompted about existing files during template merges.)*

## 4. Key Configuration Values

The behavioral rules for Genesis are governed by the project context. Ensure the following files have been correctly set up:

1. **`AGENTS.md`**: This is your single source of truth for the Agent Memory Protocol. 
   - **Notebook ID**: Update the `Notebook ID` value in `AGENTS.md` to map to your specific AntiGravity/NotebookLM MCP instance.
   - **Objective**: Ensure the project objective is clearly defined at the top of the file.
2. **`.specify/memory/constitution.md`**: This is the compiled constitution that Specify CLI agents read from. If you update `AGENTS.md`, you should use the `/speckit.constitution` command (in your agent of choice) to ensure the Spec Kit template rules are synced with `AGENTS.md`.

## 5. The Spec-Driven Workflow

Whenever you develop a new feature for Project Genesis, you must follow the Spec-Driven Development lifecycle. Access these commands using your configured AI agent (e.g., via chat in Copilot, `/` commands in Claude Code, etc.):

1. **Research & Sync Knowledge**: Run `just research-sync` to ensure your Dev notebook has the latest domain knowledge.
2. **`/speckit.specify [feature]`**: Generate the initial requirement specification (`specs/[feature]/spec.md`) based on your business logic. 
3. **`/speckit.plan`**: Generate the technical implementation plan (`specs/[feature]/plan.md`) to map the spec against the Genesis Constitution (FastAPI, HTMX, Tailwind, PostGIS).
4. **`/speckit.tasks`**: Break the plan down into actionable, sequential steps (`specs/[feature]/tasks.md`).
5. **`/speckit.implement`**: Execute the tasks one by one.

*For more details on the command bridge, refer to the "Critical Commands" section in `AGENTS.md`.*
