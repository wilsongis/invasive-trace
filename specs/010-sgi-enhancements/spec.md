# Spec 010: SGI Meeting Enhancement Suggestions

> **Feature Specification** — Southern Grassland Institute meeting outcomes, feasibility analysis, and implementation roadmap.

---

## 1. Context

On 2026-04-21, a meeting was held with the SGI team to discuss project enhancements. Six suggestions were raised. This spec documents each suggestion, its feasibility assessment, and the recommended implementation path.

---

## 2. Suggestions & Feasibility Analysis

### Suggestion 1: Add EDDMapS and iNaturalist data for ground truth

**Status: ALREADY IMPLEMENTED** ✅

The system already ingests ground truth observations from both sources:

- **Schema:** `ground_truth_observations` table with `source IN ('iNaturalist', 'EDDMapS', 'field_survey')` constraint
- **Consumers:** `app/services/inat_consumer.py` and `app/services/eddmaps_consumer.py` with retry-safe ingestion
- **Seed Script:** `app/scripts/seed_observations.py` invoked via `just seed-data`
- **API:** `POST /api/v1/observations/sync` endpoint

**Action Required:** None. Confirm with SGI team that the existing functionality meets their needs. If they want enhanced filtering (e.g., by species, date range, or ROI), that is a separate enhancement.

---

### Suggestion 2: Integrate Meta Tree Canopy Height Data

**Feasibility: HIGH** ✅

Meta's Global Canopy Height dataset provides ~10m resolution tree height estimates globally. This is valuable for:
- Identifying woody encroachment into grasslands
- Distinguishing tree cover from herbaceous vegetation
- Providing structural context for invasive species habitat modelling

**Technical Approach:**
1. **Data Source:** Meta Canopy Height Maps (https://ai.meta.com/ai-for-good/datasets/canopy-height-maps/)
   - Available as GeoTIFF tiles covering the globe at 10m resolution
   - Can be accessed via cloud storage or downloaded for local processing
2. **Ingestion Strategy:** **Pre-cache for SGI ROI polygons** — canopy height data will be computed and cached for all SGI study area polygons rather than fetched on-demand. This ensures fast dashboard queries and consistent feature availability for the Stage 2 classifier.
3. **Integration Layer:**
   - New service: `app/services/canopy_height.py` — tile fetch, mosaic, and zonal statistics
   - Extend `spectral_time_series` or create new `canopy_height_metrics` table for per-ROI height statistics
   - Add canopy height features to Stage 2 `FeatureExtractor` pipeline
4. **Schema Impact:**
   - New table `canopy_height_metrics` OR extend `spectral_time_series` with `canopy_height_mean`, `canopy_height_max`, `canopy_height_std`
   - New API endpoint: `GET /api/v1/rois/{id}/canopy-metrics`
5. **Dependencies:** Rasterio (already in stack), GeoTIFF I/O, zonal statistics computation

**Risks:**
- Data volume: Global 10m tiles are large; pre-caching limits scope to SGI study areas only
- Update frequency: Meta canopy data is annual or less frequent; not real-time

**Recommendation:** Proceed. Create spec 011 for canopy height integration.

---

### Suggestion 3: Quantify "Woody Pressure" on Grasslands

**Feasibility: MEDIUM-HIGH** ✅

Woody encroachment is a critical grassland degradation metric. Quantifying it would help SGI understand restoration costs and ecological risk.

**Technical Approach:**
1. **Woody Pressure Index (WPI)** — composite score derived from:
   - **Canopy height coverage** (from Meta data): % of ROI pixels with height > **8 feet (2.44m)**
   - **Woody spectral signature** (from Sentinel-2): NDVI texture, red-edge ratio, SWIR bands for lignin/cellulose detection
   - **Topographic context** (from USGS 3DEP): elevation, slope, aspect — woody species prefer certain microclimates
   - **Temporal trend**: rate of canopy height increase over time (if multi-temporal canopy data available)
2. **Service:** `app/services/woody_pressure.py` — computes WPI per ROI on a 0–1 scale
3. **Schema Impact:**
   - Add `woody_pressure_score FLOAT` to `invasion_predictions` table, OR
   - Create new `ecological_risk_scores` table with `roi_id`, `woody_pressure_score`, `invasive_pressure_score`, `computed_at`
4. **API Impact:**
   - Extend `GET /api/v1/rois/{id}` response to include WPI
   - New endpoint: `GET /api/v1/rois/{id}/woody-pressure` for time-series WPI

**Risks:**
- Requires canopy height data (Suggestion 2) as primary input
- Woody vs herbaceous spectral discrimination is non-trivial; may require training data
- Multi-temporal canopy data may not be available for trend analysis

**Recommendation:** Proceed, but make it dependent on Suggestion 2 (canopy height). Create spec 012 for woody pressure quantification.

---

### Suggestion 4: Separate Scores for Invasive Plants and Woody Pressure

**Feasibility: HIGH** ✅

Currently, `invasion_predictions` has:
- `confidence` — Stage 2 classifier confidence for species label
- `hotspot_score` — Stage 3 ecological spread risk (0–1)

Adding a separate woody pressure score would provide clearer ecological context.

**Technical Approach:**
1. **Schema Migration:**
   - Add `woody_pressure_score FLOAT CHECK (woody_pressure_score BETWEEN 0.0 AND 1.0)` to `invasion_predictions`
   - OR create new `ecological_risk_scores` table:
     ```sql
     CREATE TABLE ecological_risk_scores (
         id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
         roi_id          UUID REFERENCES regions_of_interest(id) ON DELETE CASCADE,
         prediction_id   UUID REFERENCES invasion_predictions(id) ON DELETE CASCADE,
         invasive_score  FLOAT NOT NULL CHECK (invasive_score BETWEEN 0.0 AND 1.0),
         woody_score     FLOAT NOT NULL CHECK (woody_score BETWEEN 0.0 AND 1.0),
         computed_at     TIMESTAMPTZ DEFAULT now()
     );
     ```
2. **API Impact:**
   - Extend `ValidationResponse` schema to include both scores
   - Dashboard template updates to display dual scores
3. **Pipeline Impact:**
   - Stage 3 U-Net or new scoring service computes both scores
   - `app/services/pipeline.py` orchestrates dual-score computation

**Risks:**
- Minimal — schema extension is straightforward
- Dashboard UI needs careful design to avoid clutter

**Recommendation:** Proceed. Bundle with Suggestion 3 implementation.

---

### Suggestion 5: Load Common Invasive Species by State

**Feasibility: HIGH** ✅

Regional species lists would improve Stage 2 classifier accuracy by constraining candidate species to those known to occur in the ROI's state.

**Technical Approach:**
1. **Data Sources:**
   - USDA PLANTS Database (https://plants.usda.gov/) — state-level occurrence data
   - EDDMapS state lists (already have API access)
   - State extension service publications
   - Invasive Species Compendium (CABI)
2. **Schema:**
   - New table `invasive_species_catalog`:
     ```sql
     CREATE TABLE invasive_species_catalog (
         id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
         species_label   TEXT NOT NULL,
         common_name     TEXT,
         state_code      TEXT NOT NULL,           -- e.g. "TX", "OK"
         status          TEXT,                    -- "invasive", "noxious", "watch_list"
         source          TEXT NOT NULL,           -- "USDA", "EDDMapS", "extension"
         last_updated    TIMESTAMPTZ DEFAULT now()
     );
     CREATE INDEX idx_isc_state ON invasive_species_catalog (state_code);
     CREATE UNIQUE INDEX idx_isc_species_state ON invasive_species_catalog (species_label, state_code, source);
     ```
3. **Service:** `app/services/species_catalog.py` — loads, queries, and filters species by state
4. **Pipeline Integration:**
   - Stage 2 `FeatureExtractor` filters candidate species by ROI state before classification
   - Reduces false positives from species not present in the region

**Risks:**
- Data quality varies by source; need deduplication and normalization
- Species labels must match between catalog and classifier training data

**Recommendation:** Proceed. Create spec 013 for invasive species catalog integration.

---

### Suggestion 6: Select Specific Counties to Pilot

**Feasibility: HIGH** ✅

Pilot counties would provide a focused test area for validation before scaling to the full SGI study region.

**Technical Approach:**
1. **Data Source:**
   - US Census TIGER/Line county boundaries (https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html)
   - Free, public, updated annually
2. **Schema:**
   - New table `pilot_counties`:
     ```sql
     CREATE TABLE pilot_counties (
         id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
         state_code      TEXT NOT NULL,
         county_name     TEXT NOT NULL,
         fips_code       TEXT NOT NULL UNIQUE,    -- 5-digit FIPS
         geom            GEOMETRY(POLYGON, 4326) NOT NULL,
         is_active       BOOLEAN DEFAULT TRUE,
         selected_at     TIMESTAMPTZ DEFAULT now()
     );
     CREATE INDEX idx_pilot_county_geom ON pilot_counties USING GIST (geom);
     ```
   - Add `pilot_county_id UUID REFERENCES pilot_counties(id)` to `regions_of_interest`
3. **API Impact:**
   - New endpoint: `GET /api/v1/pilot-counties` — list active pilot counties
   - New endpoint: `POST /api/v1/pilot-counties` — add pilot county (admin)
   - ROI creation can optionally link to a pilot county
4. **Dashboard Impact:**
   - Filter predictions by pilot county
   - Summary statistics per pilot county

**Risks:**
- Minimal — county boundaries are stable, well-documented data
- Need SGI team to select which counties to pilot

**Recommendation:** Proceed. Create spec 014 for pilot county selection and management.

---

## 3. Implementation Roadmap

| Phase | Spec | Suggestions | Priority | Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| **Wave 5.1** | `011-canopy-height-integration` | S2 | High | None |
| **Wave 5.2** | `012-woody-pressure-quantification` | S3, S4 | High | Wave 5.1 (canopy height) |
| **Wave 5.3** | `013-invasive-species-catalog` | S5 | Medium | None |
| **Wave 5.4** | `014-pilot-county-selection` | S6 | Medium | None |

**Suggestion 1** requires no implementation — already complete.

---

## 4. Schema Changes Summary

| Table | Change | Spec |
| :--- | :--- | :--- |
| `canopy_height_metrics` (new) | Per-ROI canopy height statistics | 011 |
| `invasion_predictions` | Add `woody_pressure_score FLOAT` | 012 |
| `invasive_species_catalog` (new) | State-level invasive species reference | 013 |
| `pilot_counties` (new) | US county boundaries for pilot areas | 014 |

---

## 5. Open Questions for SGI Team

1. **Suggestion 1:** ~~Do you need enhanced filtering on ground truth observations (by species, date, ROI)?~~ **ANSWERED** — Hold off on filters for now. No changes needed.
2. **Suggestion 2:** ~~Should canopy height data be ingested on-demand (per ROI) or pre-cached for all study areas?~~ **ANSWERED** — Pre-cache for SGI ROI polygons (locations).
3. **Suggestion 3:** ~~What threshold defines "woody" vs "herbaceous" for your ecological models?~~ **ANSWERED** — Use 8 feet (2.44m) as the canopy height threshold.
4. **Suggestion 5:** ~~Which states are in scope for the invasive species catalog?~~ **ANSWERED** — 25 states confirmed (TX, LA, MS, AL, GA, FL, SC, NC, VA, TN, AR, OK, KS, MO, KY, WV, MD, DE, NJ, PA, OH, IN, IL, NY, CT). See Section 8.
5. **Suggestion 6:** ~~Which specific counties should be selected as pilot areas? Please provide state + county names or FIPS codes.~~ **ANSWERED** — see Section 7.

---

## 6. Checklist

- [x] Feasibility analysis complete for all 6 suggestions
- [x] SGI team review and feedback (partial — pilot counties confirmed)
- [ ] Spec 011: Canopy height integration
- [ ] Spec 012: Woody pressure quantification
- [ ] Spec 013: Invasive species catalog
- [ ] Spec 014: Pilot county selection
- [ ] AGENTS.md update with new schema contracts

---

## 7. Pilot County Selections (Confirmed)

The following counties have been confirmed as pilot areas for Wave 5.4:

| County | State | FIPS Code | Notes |
| :--- | :--- | :--- | :--- |
| Montgomery County | TN | 47125 | "YN" interpreted as Tennessee (TN) |
| Cherokee County | GA | 13057 | North of Atlanta, grassland/woodland interface |
| Forsyth County | GA | 13117 | "Forsythe" corrected to Forsyth; rapid development pressure |

**Note:** "Montgomery County, YN" was interpreted as Tennessee (TN) since "YN" is not a valid state code. If this is incorrect (e.g., meant to be another state), please clarify.

These three counties will be loaded into the `pilot_counties` table during Wave 5.4 implementation using US Census TIGER/Line boundary data.

---

## 8. SGI Study Area States & Invasive Species Catalog

The following 25 states are confirmed as the SGI study area scope. The invasive species catalog (Wave 5.3) will be populated with species data for these states.

| State | Code | Key Invasive Species |
| :--- | :--- | :--- |
| Texas | TX | Chinese tallow, Chinese privet, Japanese honeysuckle, kudzu, Chinese wisteria, giant reed, saltcedar, old world bluestems, King Ranch bluestem, Johnsongrass, glossy privet, chinaberry |
| Louisiana | LA | Chinese tallow, Chinese privet, Japanese climbing fern, cogongrass, Chinese wisteria, Japanese honeysuckle, kudzu, chinaberry, Chinese parasoltree, nandina, mimosa, saltcedar |
| Mississippi | MS | Kudzu, cogongrass, Chinese tallow, Chinese privet, Japanese honeysuckle, Chinese wisteria, mimosa, tropical soda apple, torpedograss, privet, sericea lespedeza, tall fescue |
| Alabama | AL | Cogongrass, Chinese privet, kudzu, Japanese climbing fern, Chinese tallow, mimosa, Chinese wisteria, Japanese honeysuckle, tree-of-heaven, sericea lespedeza, nandina, tallowtree |
| Georgia | GA | Tree-of-heaven, Chinese privet, Japanese honeysuckle, kudzu, Chinese wisteria, mimosa, autumn olive, English ivy, Chinese tallow, nandina, Japanese climbing fern, Nepalese browntop |
| Florida | FL | Cogongrass, air potato, coral ardisia, Caesar weed, camphor tree, Chinese tallow, tropical soda apple, skunk vine, rosary pea, melaleuca, downy rose myrtle, earleaf acacia |
| South Carolina | SC | Chinese privet, Japanese honeysuckle, kudzu, Chinese tallow, tree-of-heaven, autumn olive, multiflora rose, mimosa, Japanese stiltgrass, sericea lespedeza, Nepalese browntop, Chinese silvergrass |
| North Carolina | NC | Tree-of-heaven, Japanese stiltgrass, Chinese privet, Japanese honeysuckle, kudzu, Chinese wisteria, autumn olive, multiflora rose, mimosa, privet, English ivy, Nepalese browntop |
| Virginia | VA | Tree-of-heaven, Japanese stiltgrass, garlic mustard, Japanese barberry, bush honeysuckles, Chinese privet, autumn olive, multiflora rose, oriental bittersweet, Japanese knotweed, mile-a-minute, wavyleaf basketgrass |
| Tennessee | TN | Chinese privet, Japanese honeysuckle, kudzu, tree-of-heaven, mimosa, autumn olive, bush honeysuckles, Japanese stiltgrass, sericea lespedeza, Nepalese browntop, Chinese silvergrass, callery pear |
| Arkansas | AR | Chinese privet, Japanese honeysuckle, Chinese wisteria, mimosa, English ivy, running bamboo, monkey grass, vinca, tall fescue, Chinese tallow, cogongrass, Bradford pear |
| Oklahoma | OK | Eastern redcedar, Japanese honeysuckle, Japanese stiltgrass, Johnsongrass, kudzu, mimosa, privet, poison hemlock, beefsteak plant, bull thistle, kochia, tree-of-heaven |
| Kansas | KS | Sericea lespedeza, old world bluestems, yellow bluestem, Caucasian bluestem, Johnsongrass, saltcedar, autumn olive, bush honeysuckles, black locust, callery pear, leafy spurge, hoary cress |
| Missouri | MO | Bush honeysuckles, autumn olive, sericea lespedeza, Japanese honeysuckle, tree-of-heaven, garlic mustard, Japanese stiltgrass, callery pear, wintercreeper, oriental bittersweet, Japanese knotweed, privet |
| Kentucky | KY | Bush honeysuckles, Japanese honeysuckle, tree-of-heaven, autumn olive, callery pear, wintercreeper, garlic mustard, Japanese stiltgrass, privet, sericea lespedeza, kudzu, Japanese knotweed |
| West Virginia | WV | Tree-of-heaven, garlic mustard, Japanese barberry, Asian bittersweet, autumn olive, bush honeysuckles, Japanese knotweed, Japanese stiltgrass, multiflora rose, privet, Norway maple, cheatgrass |
| Maryland | MD | Porcelainberry, tree-of-heaven, Japanese stiltgrass, garlic mustard, multiflora rose, Japanese honeysuckle, bush honeysuckles, Japanese barberry, wintercreeper, oriental bittersweet, Japanese knotweed, mile-a-minute |
| Delaware | DE | Japanese honeysuckle, multiflora rose, autumn olive, bush honeysuckles, Japanese stiltgrass, garlic mustard, oriental bittersweet, porcelainberry, Japanese knotweed, tree-of-heaven, wintercreeper, callery pear |
| New Jersey | NJ | Japanese stiltgrass, multiflora rose, porcelainberry, Japanese barberry, bush honeysuckles, oriental bittersweet, Japanese knotweed, tree-of-heaven, garlic mustard, autumn olive, wintercreeper, callery pear |
| Pennsylvania | PA | Japanese knotweed, mile-a-minute, Japanese stiltgrass, garlic mustard, tree-of-heaven, multiflora rose, bush honeysuckles, autumn olive, Japanese barberry, oriental bittersweet, privet, wintercreeper |
| Ohio | OH | Bush honeysuckles, autumn olive, multiflora rose, garlic mustard, Japanese knotweed, oriental bittersweet, Japanese honeysuckle, reed canary grass, purple loosestrife, callery pear, tree-of-heaven, Japanese stiltgrass |
| Indiana | IN | Bush honeysuckles, autumn olive, blunt-leaved privet, Japanese honeysuckle, Japanese hops, Japanese knotweed, oriental bittersweet, periwinkle, reed canary grass, callery pear, wintercreeper, tree-of-heaven |
| Illinois | IL | Amur honeysuckle, Johnson grass, oriental bittersweet, Japanese stiltgrass, garlic mustard, callery pear, Japanese chaff flower, bush honeysuckles, autumn olive, tree-of-heaven, reed canary grass, multiflora rose |
| New York | NY | Japanese knotweed, oriental bittersweet, garlic mustard, wild parsnip, Japanese barberry, bush honeysuckles, multiflora rose, tree-of-heaven, Japanese stiltgrass, swallow-worts, mugwort, autumn olive |
| Connecticut | CT | Japanese barberry, oriental bittersweet, Japanese knotweed, Japanese stiltgrass, multiflora rose, tree-of-heaven, garlic mustard, autumn olive, bush honeysuckles, Norway maple, winged euonymus, porcelainberry |

**Note:** New Jersey does not maintain a single official state invasive plant list; the NJ list above is synthesized from NJDEP/NJISST/Rutgers guidance.
