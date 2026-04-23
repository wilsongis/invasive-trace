# Active Context: Invasive Trace

## Current Work Focus
Spec 010 (SGI Meeting Enhancements) has been authored. The next wave of work is **Wave 5** — four new specs derived from the 2026-04-21 SGI meeting.

### Active Spec: 010-sgi-enhancements
- Feasibility analysis complete for all 6 SGI suggestions
- SGI answers received: pilot counties confirmed, 25 study states confirmed, canopy height threshold = 8 ft (2.44m), pre-cache strategy confirmed
- Specs 011–014 need to be authored before implementation begins

## Next Steps
1. Author `specs/011-canopy-height-integration/` — Meta Canopy Height data ingestion + per-ROI zonal statistics
2. Author `specs/012-woody-pressure-quantification/` — WPI composite score (canopy + spectral + topo); depends on spec 011
3. Author `specs/013-invasive-species-catalog/` — USDA PLANTS + EDDMapS state species lists for 25 states
4. Author `specs/014-pilot-county-selection/` — TIGER/Line county boundaries; 3 pilot counties pre-loaded
5. Implement Wave 5.1–5.4 in dependency order

## Recent Decisions & Context
- **AlphaEarth benchmark: no-go** — baseline RF F1=0.4373 vs benchmark F1=0.3750; Planetary Computer baseline unchanged
- **Canopy height threshold:** 8 feet (2.44m) for woody vs herbaceous classification (SGI confirmed)
- **Canopy ingestion strategy:** Pre-cache for SGI ROI polygons only (not on-demand)
- **Pilot counties (Wave 5.4):** Montgomery County TN (FIPS 47125), Cherokee County GA (13057), Forsyth County GA (13117)
- **Species catalog states (Wave 5.3):** 25 states: TX, LA, MS, AL, GA, FL, SC, NC, VA, TN, AR, OK, KS, MO, KY, WV, MD, DE, NJ, PA, OH, IN, IL, NY, CT

## Active Patterns & Preferences
- All specs follow the standard artifact set: `spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`
- All implementations must pass `just verify` (ruff + pytest) before pillar completion
- Schema changes always require an Alembic migration and AGENTS.md update
- External API consumers must handle HTTP 429 with exponential backoff (max 3 retries)
- `invasion_predictions.model_version` stores Stage 2 version only (`rf-v0.1.0`)

## Important File Locations
- `AGENTS.md` — single source of truth for schema, API contracts, ML registry
- `specs/010-sgi-enhancements/` — SGI meeting outcomes and roadmap
- `app/services/` — all business logic services
- `app/ml/` — Stage 1/2/3 ML models
- `app/scripts/` — CLI entrypoints (`just` commands invoke these)
- `migrations/versions/` — Alembic migration chain (0001→0004 currently)
- `tests/unit/` + `tests/integration/` — quality gate tests