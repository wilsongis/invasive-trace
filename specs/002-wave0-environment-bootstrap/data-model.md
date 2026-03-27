# Data Model: Wave 0 - Environment Bootstrap

Wave 0 does not introduce the canonical domain tables. It defines the bootstrap entities and configuration surfaces required to validate the runtime.

## Bootstrap Entities

### Runtime Settings

| Field | Type | Source | Purpose |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | string | env | Async connection string for PostGIS |
| `INAT_API_KEY` | string | env | Reserved for later waves; validated by settings loader |
| `EDDMAPS_API_KEY` | string | env | Reserved for later waves; validated by settings loader |
| `PC_SDK_SUBSCRIPTION_KEY` | string | env | Reserved for Planetary Computer auth |
| `LOG_LEVEL` | string | env | Runtime logging verbosity |

### Database Access Layer

| Component | Type | Purpose |
| :--- | :--- | :--- |
| `engine` | AsyncEngine | Shared SQLAlchemy engine for the app |
| `session_factory` | async_sessionmaker | Creates `AsyncSession` instances |
| `get_db` | FastAPI dependency | Injects an `AsyncSession` into request handlers |

### Bootstrap Runtime

| Component | Type | Purpose |
| :--- | :--- | :--- |
| `/healthz` | HTTP endpoint | Verifies the app is running |
| `/api/v1` | Router prefix | Establishes versioned API shape without domain features |
| Alembic baseline | migration config | Prepares Wave 1 schema migrations |

## Deferred Domain Model

The following domain tables are explicitly deferred to Wave 1 and remain governed by `AGENTS.md` Section 4:

- `regions_of_interest`
- `invasion_predictions`
- `ground_truth_observations`
- `spectral_time_series`
