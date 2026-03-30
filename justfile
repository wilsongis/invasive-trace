set shell := ["bash", "-c"]

# --- Notebook Configuration ---
# gaia-atlas (Dev) — Invasive Trace Remote Sensing & Ecology Research
DEV_ID := "b22e0bd5-8d0b-4173-a447-2b2442430d6e"
PROD_ID := "9z8y7x6w-prod-id"

# The 'notebook' variable defaults to 'dev' unless overridden in the command line
notebook := "dev"

# Internal logic to select the ID based on the variable
ACTUAL_ID := if notebook == "prod" { PROD_ID } else { DEV_ID }
NOTEBOOK_NAME := if notebook == "prod" { "PRODUCTION-KNOWLEDGE" } else { "gaia-atlas" }

IMAGE_NAME := "invasive-trace-app"
CONTAINER_NAME := "invasive-trace-app"

# ------------------------------------------------------------------------------
# 1. CORE EXECUTION
# ------------------------------------------------------------------------------

# Default: Show available commands
default:
    @just --list

# Build container if needed and start the full compose stack (app + PostGIS)
start:
    @echo "🚀 Starting Invasive Trace compose stack..."
    podman compose up --build -d
    @echo "✅ Stack is live — API: http://localhost:8000 | DB: localhost:5432"

# Stop and remove all compose containers
stop:
    podman compose down

# Build/Rebuild the container image
build:
    @echo "🛠️ Building Podman image..."
    podman build -t {{IMAGE_NAME}} .

# Start the server natively (Fastest for dev — requires local PostGIS)
run:
    @echo "🏃 Starting FastAPI natively via UV..."
    uv run fastapi dev app/main.py

# ------------------------------------------------------------------------------
# 2. RESEARCH & MEMORY (The Legacy Mentor Bridge)
# ------------------------------------------------------------------------------

# Connect / initialise the MCP server to the gaia-atlas notebook.
# Run this once after cloning, or after updating the notebook ID.
research-sync:
    @echo "🧠 Initialising MCP connection → {{NOTEBOOK_NAME}} (ID: {{ACTUAL_ID}})"
    uv tool run notebooklm-mcp init {{ACTUAL_ID}}

# Test the MCP connection to the active notebook
research-test:
    @echo "🔬 Testing connection → {{NOTEBOOK_NAME}} (ID: {{ACTUAL_ID}})"
    uv tool run notebooklm-mcp test -n {{ACTUAL_ID}}

# Start the NotebookLM MCP server (for VS Code / Copilot integration)
research-serve:
    @echo "🚀 Starting NotebookLM MCP server for {{NOTEBOOK_NAME}}..."
    uv tool run notebooklm-mcp server

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

# Apply Alembic migrations against the running PostGIS container
db-migrate:
    @echo "🗄️  Running Alembic migrations..."
    uv run alembic upgrade head
    @echo "✅ Migrations applied."

# Roll back the last Alembic migration
db-rollback:
    uv run alembic downgrade -1

# Autogenerate a new Alembic migration from model changes
db-revision msg="": 
    uv run alembic revision --autogenerate -m "{{msg}}"

# Seed ground-truth observations from iNaturalist + EDDMapS
seed-data:
    @echo "🌱 Seeding ground-truth observations..."
    uv run python -m app.scripts.seed_observations
    @echo "✅ Seed complete."

# Dry-run seed workflow (fetch + summary, no DB writes)
seed-data-dry-run:
    @echo "🌱 Dry-run seeding ground-truth observations..."
    uv run python -m app.scripts.seed_observations --dry-run
    @echo "✅ Dry-run seed complete."

# Verify standard: run linters, formatters, and tests
verify: lint test
    @echo "✅ Verification complete! Environment is fully compliant."