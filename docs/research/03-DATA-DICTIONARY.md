# Data Dictionary — Invasive Trace

> All geometry columns use SRID 4326 (WGS84). See `AGENTS.md` Section 4 for the canonical DDL.

## `regions_of_interest`
| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | UUID | PK, default gen_random_uuid() | Surrogate key |
| `name` | TEXT | NOT NULL | Human-readable ROI name |
| `description` | TEXT | | Optional narrative |
| `geom` | GEOMETRY(POLYGON,4326) | NOT NULL, GiST index | WGS84 study area polygon |
| `created_at` | TIMESTAMPTZ | default now() | Record creation time |
| `updated_at` | TIMESTAMPTZ | default now() | Last modification time |

## `invasion_predictions`
| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | UUID | PK | Surrogate key |
| `roi_id` | UUID | FK → regions_of_interest | Parent study area |
| `species_label` | TEXT | NOT NULL | e.g. `"Bromus tectorum"` |
| `confidence` | FLOAT | CHECK 0.0–1.0 | Stage 2 model confidence |
| `hotspot_score` | FLOAT | | Stage 3 spread risk (0–1) |
| `geom` | GEOMETRY(POINT,4326) | NOT NULL, GiST index | Prediction centroid |
| `model_version` | TEXT | NOT NULL | Stage 2 classifier version used to assign `species_label` + `confidence`, e.g. `"rf-v0.1.0"` |
| `predicted_at` | TIMESTAMPTZ | default now() | Inference timestamp |
| `validated` | BOOLEAN | nullable | HITL review state: `NULL` pending, `TRUE` confirmed, `FALSE` rejected |
| `validator_notes` | TEXT | | Free-text reviewer comment |

## `ground_truth_observations`
| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | UUID | PK | Surrogate key |
| `source` | TEXT | CHECK IN ('iNaturalist','EDDMapS','field_survey') | Record provenance |
| `external_id` | TEXT | | Original source record ID |
| `species_label` | TEXT | NOT NULL | Taxonomic name |
| `observer` | TEXT | | Observer name/username |
| `observed_at` | DATE | | Field observation date |
| `geom` | GEOMETRY(POINT,4326) | NOT NULL, GiST index | Observation location |
| `is_confirmed` | BOOLEAN | default TRUE | Expert-confirmed flag |
| `raw_payload` | JSONB | | Full API response |

## `spectral_time_series`
| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | UUID | PK | Surrogate key |
| `roi_id` | UUID | FK → regions_of_interest | Parent study area |
| `scene_date` | DATE | NOT NULL | Acquisition date |
| `platform` | TEXT | CHECK IN ('sentinel-2','landsat-hls','naip') | Sensor platform |
| `stac_item` | TEXT | NOT NULL | Planetary Computer STAC item ID |
| `ndvi` | FLOAT | | (NIR−Red)/(NIR+Red) |
| `endvi` | FLOAT | | Enhanced NDVI (red-edge) |
| `red_edge` | FLOAT | | Red Edge Chlorophyll Index |
| `cloud_cover` | FLOAT | | Scene-level cloud fraction (QA60) |
| `is_masked` | BOOLEAN | default FALSE | TRUE if cloud_cover > 0.20 |
