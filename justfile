set shell := ["bash", "-c"]

# --- Notebook Configuration ---
# Default IDs (Replace with your actual IDs from NotebookLM URLs)
DEV_ID := "1a2b3c4d-dev-id"
PROD_ID := "9z8y7x6w-prod-id"

# The 'notebook' variable defaults to 'dev' unless overridden in the command line
notebook := "dev"

# Internal logic to select the ID based on the variable
ACTUAL_ID := if notebook == "prod" { PROD_ID } else { DEV_ID }
NOTEBOOK_NAME := if notebook == "prod" { "PRODUCTION-KNOWLEDGE" } else { "DEVELOPMENT-SANDBOX" }

IMAGE_NAME := "genesis-image"
CONTAINER_NAME := "genesis-app"

# ------------------------------------------------------------------------------
# 1. CORE EXECUTION
# ------------------------------------------------------------------------------

# Default: Show available commands
default:
    @just --list

# Build container if needed and start the server
start:
    @echo "🚀 Checking container status..."
    @if [ ! "$$(podman ps -aq -f name={{CONTAINER_NAME}})" ]; then \
        echo "📦 Container not found. Building..."; \
        just build; \
    fi
    @podman start {{CONTAINER_NAME}} || podman run -d --name {{CONTAINER_NAME}} -p 8000:8000 {{IMAGE_NAME}}
    @echo "✅ Server is live at http://localhost:8000"

# Build/Rebuild the container image
build:
    @echo "🛠️ Building Podman image..."
    podman build -t {{IMAGE_NAME}} .

# Start the server natively (Fastest for dev)
run:
    @echo "🏃 Starting FastAPI natively via UV..."
    uv run fastapi dev main.py

# ------------------------------------------------------------------------------
# 2. RESEARCH & MEMORY (The Legacy Mentor Bridge)
# ------------------------------------------------------------------------------

research-sync:
    @echo "🧠 Target: {{NOTEBOOK_NAME}} (ID: {{ACTUAL_ID}})"
    uv tool run notebooklm-mcp sync --id {{ACTUAL_ID}} ./docs/research/

# Open the selected notebook in the browser
research-open:
    @echo "🌐 Opening {{NOTEBOOK_NAME}}..."
    open "https://notebooklm.google.com/notebook/{{ACTUAL_ID}}"

# Check current active context
research-status:
    @echo "Current Grounding Source: {{NOTEBOOK_NAME}}"
    @echo "Current Notebook ID: {{ACTUAL_ID}}"

# ------------------------------------------------------------------------------
# 3. MAINTENANCE & QUALITY
# ------------------------------------------------------------------------------

# Initialize a new project from the Genesis template
init:
    @if [ ! -f "AGENTS.md" ]; then cp templates/AGENTS.md.template AGENTS.md; fi
    uv venv
    uv pip install -e .
    @echo "✨ Project Initialized. Memory Protocol Active."

# Run linting and formatting
lint:
    uv run ruff check . --fix
    uv run ruff format .

# Run the test suite
test:
    uv run pytest

# Verify standard: run linters, formatters, and tests
verify: lint test
    @echo "✅ Verification complete! Environment is fully compliant."