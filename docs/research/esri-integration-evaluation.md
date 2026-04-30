# Esri/ArcGIS Integration Evaluation for Invasive Trace at APSU GIS Center

**Date:** 2026-04-30  
**Evaluator:** Roo (Architect Mode)  
**Context:** APSU GIS Center (Esri shop with Esri-enabled PostgreSQL) evaluating Invasive Trace API backend integration with Esri Invasive Vegetation Management solution

---

## Executive Summary

Invasive Trace is a modern FastAPI + PostgreSQL/PostGIS system with a 3-stage AI pipeline for invasive species detection. The APSU GIS Center's existing Esri ecosystem and the Esri Invasive Vegetation Management solution present both opportunities and challenges for integration. **Recommendation: Pursue a hybrid integration approach** — expose Invasive Trace as ArcGIS-compatible services while keeping the ML pipeline intact, rather than a full replacement.

---

## 1. Technical Feasibility Analysis

### 1.1 Invasive Trace Current Capabilities
- **Backend:** FastAPI with async SQLAlchemy + GeoAlchemy2
- **Database:** PostgreSQL 16 + PostGIS 3.4 (WGS84/EPSG:4326)
- **Spatial Data:** Already stored as PostGIS geometry types (POLYGON for ROIs, POINT for predictions/observations)
- **API:** RESTful endpoints with GeoJSON output (`/api/v1/predictions` returns FeatureCollection)
- **ML Pipeline:** 3-stage AI chain (AnomalyDetector → FocalClassifier → UNetTexture)

### 1.2 Esri Invasive Vegetation Management Solution Requirements
Based on Esri's solution architecture (from provided documentation links):

**Required Data Layers:**
- **Infestation Points/Areas** — Invasive species occurrence locations (maps to `invasion_predictions` + `ground_truth_observations`)
- **Treatment Areas** — Management action polygons (NOT currently in Invasive Trace schema)
- **Survey Polygons** — Monitoring regions (maps to `regions_of_interest`)
- **Chemical/Mechanical Treatment Records** — Treatment history (NOT in schema)
- **Species Reference Table** — Taxonomic lookup (partial: `species_label` exists but no formal taxonomy table)

**Esri Data Model Expectations:**
- Feature Services with specific field names (e.g., `Species`, `InfestationStatus`, `TreatmentDate`)
- Relationship classes between infestations → treatments → surveys
- Attachment support for field photos
- Versioned editing capability (for multi-user editing workflows)

### 1.3 Compatibility Assessment

| Invasive Trace Component | Esri Solution Match | Gap? |
|-------------------------|---------------------|------|
| `regions_of_interest` (POLYGON) | Survey/Monitoring Areas | ✅ Direct match |
| `invasion_predictions` (POINT) | Infestation Points | ⚠️ Partial (needs status field mapping) |
| `ground_truth_observations` (POINT) | Infestation Verification | ✅ Direct match |
| `spectral_time_series` | NOT in Esri solution | ℹ️ Invasive Trace unique value-add |
| Treatment tracking | Required by Esri | ❌ **Missing** |
| Chemical/mechanical treatment history | Required by Esri | ❌ **Missing** |
| Species taxonomy table | Recommended by Esri | ❌ **Missing** |
| Attachment support | Required by Esri | ❌ **Missing** |

**Verdict:** Moderate feasibility with schema extensions needed.

---

## 2. Data Model Compatibility

### 2.1 PostGIS (Invasive Trace) vs Esri Geodatabase

**Shared Foundation:**
- Both use PostgreSQL as the underlying database
- APSU GIS Center already has "Esri-enabled PostgreSQL" — meaning the database has ST_Geometry or PostGIS with Esri's ArcSDE/Enterprise Geodatabase schema

**Key Difference:**
- **Invasive Trace:** Pure PostGIS (`GEOMETRY(POINT, 4326)`) with GeoAlchemy2 ORM
- **Esri Enterprise Geodatabase:** Adds Esri-specific system tables (`sde_*`, `gdb_*`), uses either ST_Geometry (Esri's spatial type) or PostGIS with Esri's versioning/attachment framework

**Coexistence Options:**

| Approach | Pros | Cons |
|----------|------|------|
| **Side-by-side databases** | Clean separation; no schema conflicts | Dual maintenance; data sync needed |
| **Single DB, separate schemas** | Unified backup/restore; cross-schema queries possible | Risk of Esri overwriting PostGIS functions |
| **Single DB, Esri-enabled with PostGIS** | APSU may already have this | Complex; Esri + PostGIS function conflicts possible |

**Recommendation:** Use separate PostgreSQL schemas within the same database:
- `invasive_trace.*` — Invasive Trace tables (already exists)
- `sde.*` or `gis.*` — Esri system tables
- `invasive_trace_esri.*` — Esri-compatible views/materialized views

### 2.2 Schema Mapping Strategy

Create **Esri-compatible views** in PostgreSQL:

```sql
-- Example: Map invasion_predictions to Esri Infestation Points schema
CREATE VIEW invasive_trace_esri.infestation_points AS
SELECT 
    id::text AS globalid,  -- Esri expects GUID string
    species_label AS species,
    CASE 
        WHEN validated = TRUE THEN 'Confirmed'
        WHEN validated = FALSE THEN 'Rejected'
        ELSE 'Pending Review'
    END AS infestation_status,
    confidence AS confidence_score,
    hotspot_score AS risk_rating,
    predicted_at AS detection_date,
    geom AS shape  -- Esri can read PostGIS geometry
FROM invasion_predictions;
```

---

## 3. API Integration Strategy

### 3.1 Current Invasive Trace API Endpoints

| Endpoint | Method | Purpose | Esri Compatibility |
|----------|--------|---------|-------------------|
| `/api/v1/rois` | GET/POST | ROI management | ✅ Can map to Survey Areas |
| `/api/v1/predictions` | GET | GeoJSON FeatureCollection | ✅ **Directly consumable by ArcGIS** |
| `/api/v1/predictions/{id}/validate` | PATCH | HITL validation | ⚠️ Needs Esri Feature Service edit capability |
| `/api/v1/scenes/ingest` | POST | STAC scene ingestion | ℹ️ Backend-only; not needed in Esri frontend |
| `/api/v1/observations/sync` | POST | Ground truth seeding | ℹ️ Backend-only; not needed in Esri frontend |
| `/api/v1/metrics/*` | GET | Model performance metrics | ℹ️ Admin-only; not needed in Esri frontend |
| `/api/v1/protocols/*` | GET/POST | SGI protocols | ℹ️ New feature; may need Esri exposure |

### 3.2 Integration Patterns

#### Option A: Direct GeoJSON Consumption (Simplest)
```
Invasive Trace API → GeoJSON → ArcGIS Pro/Portal (Add Data from Path)
```
- **Pros:** Zero middleware; Invasive Trace already outputs GeoJSON (`PredictionFeatureCollection`)
- **Cons:** Read-only; no editing from Esri; no relationship classes

#### Option B: ArcGIS Enterprise Feature Service (Recommended)
```
Invasive Trace DB → Esri-compatible views → ArcGIS Server/Portal Feature Service
```
- **Pros:** Full editing capability; versioning; attachments; relationships
- **Cons:** Requires Esri Enterprise setup; view maintenance

#### Option C: Middleware Translation Layer
```
Invasive Trace API → Python middleware → Esri REST API (Feature Service)
```
- **Pros:** Decouples systems; can handle complex transformations
- **Cons:** Additional maintenance; potential performance bottleneck

**Recommendation:** **Option B** — Create Esri-compatible database views and register them as ArcGIS Feature Services. This leverages APSU's existing Esri infrastructure.

---

## 4. Esri-Enabled PostgreSQL Considerations

### 4.1 APSU GIS Center Context
- Already using "Esri-enabled PostgreSQL" — likely means ArcGIS Enterprise registered database
- May be using ST_Geometry or PostGIS with Esri's enterprise geodatabase framework
- Probably has versioning enabled (traditional or branch)

### 4.2 Coexistence Strategy

**Critical Rule:** Never let Esri's ArcGIS tools modify Invasive Trace's tables directly. Use views or a separate schema.

**Recommended Setup:**
```
PostgreSQL Database: invasive_trace_db
├── public (default, unused)
├── invasive_trace (Invasive Trace tables: regions_of_interest, invasion_predictions, etc.)
├── invasive_trace_esri (Esri-compatible views + additional tables like treatments)
├── sde (Esri system tables, if using Enterprise Geodatabase)
└── gis (Esri data schema, if using ArcGIS Pro with PostGIS)
```

**Database Permissions:**
- Invasive Trace service account: `GRANT ALL ON SCHEMA invasive_trace`
- Esri ArcGIS service account: `GRANT SELECT ON invasive_trace_esri.*` (read-only on views)
- Esri editing users: `GRANT ALL ON invasive_trace_esri.treatment_areas` (write on treatment tables)

---

## 5. Pros/Cons Analysis

### 5.1 Full Replacement (Replace Invasive Trace Frontend with Esri Solution)

**Pros:**
- ✅ Leverages APSU's existing Esri expertise
- ✅ Pre-built invasive vegetation workflows (survey → treatment → monitoring)
- ✅ Mobile data collection via ArcGIS Field Maps
- ✅ Integration with ArcGIS Pro/Portal ecosystem

**Cons:**
- ❌ **Loses Invasive Trace's 3-stage AI pipeline** (core value proposition)
- ❌ Esri solution lacks remote sensing integration (Planetary Computer STAC)
- ❌ No ML-driven prediction capability in Esri solution
- ❌ Significant rework of backend data ingestion
- ❌ Vendor lock-in to Esri

**Verdict:** ❌ **Not recommended** — throws away Invasive Trace's core differentiators.

### 5.2 Hybrid Approach (Keep Invasive Trace Backend + Add Esri Frontend)

**Pros:**
- ✅ Preserves Invasive Trace's AI/ML pipeline (Stage 1-3)
- ✅ Adds Esri's field data collection (ArcGIS Field Maps)
- ✅ Leverages APSU's Esri expertise for visualization/mapping
- ✅ Invasive Trace handles detection; Esri handles treatment workflows
- ✅ Gradual migration path

**Cons:**
- ⚠️ Requires schema extensions (treatment tables, species taxonomy)
- ⚠️ Data synchronization complexity (predictions → Esri Feature Service)
- ⚠️ Dual maintenance of two systems
- ⚠️ User training on two interfaces

**Verdict:** ✅ **Recommended** — best of both worlds.

### 5.3 API-Only Integration (Expose Invasive Trace as ArcGIS-Compatible Services)

**Pros:**
- ✅ Minimal changes to Invasive Trace
- ✅ Esri consumes GeoJSON/Feature Services directly
- ✅ Clean separation of concerns

**Cons:**
- ⚠️ Limited to read-only operations from Esri
- ⚠️ No treatment workflow support
- ⚠️ Misses Esri's field data collection value

**Verdict:** ⚠️ **Partial solution** — good starting point, but limited long-term.

---

## 6. Architecture Recommendations

### 6.1 Recommended Architecture: Hybrid with Esri-Compatible Data Layer

```
┌─────────────────────────────────────────────────────────────────────┐
│  APSU GIS Center Ecosystem                                          │
│                                                                     │
│  ┌──────────────────────┐      ┌──────────────────────────────┐    │
│  │  Esri Frontend       │      │  Invasive Trace Backend      │    │
│  │  ┌────────────────┐  │      │  ┌────────────────────────┐  │    │
│  │  │ ArcGIS Pro     │  │      │  │ FastAPI (Python 3.12)  │  │    │
│  │  │ ArcGIS Portal  │  │      │  │  ┌──────────────────┐  │  │    │
│  │  │ Field Maps     │  │      │  │  │ /api/v1/*        │  │  │    │
│  │  │ Dashboards    │  │      │  │  │ GeoJSON output   │  │  │    │
│  │  └────────────────┘  │      │  │  └──────────────────┘  │  │    │
│  │         ▲              │      │  │          ▲               │  │    │
│  │         │              │      │  │          │               │  │    │
│  │         ▼              │      │  │          ▼               │  │    │
│  │  ┌────────────────┐  │      │  │  ┌──────────────────┐  │  │    │
│  │  │ Feature       │◄─┼──────┼──┼──│──│ DB Views / API  │  │  │    │
│  │  │ Services      │  │      │  │  │  └──────────────────┘  │  │    │
│  │  └────────────────┘  │      │  │          ▲               │  │    │
│  │         ▲              │      │  │          │               │  │    │
│  └─────────┼──────────────┘      │  │          ▼               │  │    │
│            │                     │  │  ┌──────────────────┐  │  │    │
│            │                     │  │  │ PostgreSQL +     │  │  │    │
│            │                     │  │  │ PostGIS          │  │  │    │
│            │                     │  │  │ ┌──────────────┐ │  │  │    │
│            │                     │  │  │ │ invasive_    │ │  │  │    │
│            │                     │  │  │ │ trace schema  │ │  │  │    │
│            │                     │  │  │ └──────────────┘ │  │  │    │
│            │                     │  │  │ ┌──────────────┐ │  │  │    │
│            │                     │  │  │ │ esri_compat  │ │  │  │    │
│            │                     │  │  │ │ views/tables │ │  │  │    │
│            │                     │  │  │ └──────────────┘ │  │  │    │
│            │                     │  │  └──────────────────┘  │  │    │
│            │                     │  └────────────────────────┘  │    │
│            │                     └──────────────────────────────┘    │
│            │                                                          │
│  ┌─────────┴──────────────────────────────────────────────┐          │
│  │  External Data Sources                                │          │
│  │  Planetary Computer (STAC) • iNaturalist • EDDMapS    │          │
│  └───────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Data Flow

1. **Detection Pipeline (Invasive Trace):**
   - Planetary Computer STAC → Scene ingestion → Spectral indices → Stage 1-3 ML → `invasion_predictions` table

2. **Esri Exposure (Database Views):**
   - `invasive_trace_esri.infestation_points` view → Registered as ArcGIS Feature Service
   - `invasive_trace_esri.survey_areas` view → Registered as ArcGIS Feature Service

3. **Field Workflow (Esri):**
   - ArcGIS Field Maps → Collect treatment data → `invasive_trace_esri.treatment_areas` table
   - ArcGIS Dashboard → Visualize predictions + treatments

4. **Feedback Loop (Optional):**
   - Esri validation → PATCH `/api/v1/predictions/{id}/validate` → Update `validated` field

---

## 7. Implementation Complexity Assessment

### 7.1 Schema Extensions Required

| New Table/View | Purpose | Complexity |
|----------------|---------|------------|
| `treatment_areas` | Store treatment actions (Esri requirement) | Low (new table) |
| `species_taxonomy` | Reference table for species (Esri best practice) | Low (new table) |
| `infestation_points_view` | Esri-compatible view of `invasion_predictions` | Medium (field mapping) |
| `survey_areas_view` | Esri-compatible view of `regions_of_interest` | Low |
| `treatment_areas_view` | Esri-compatible view of `treatment_areas` | Low |

### 7.2 Code Changes

| Component | Change Required | Complexity |
|-----------|----------------|------------|
| `app/models/` | Add `TreatmentArea`, `SpeciesTaxonomy` ORM models | Low |
| `migrations/versions/` | Alembic migration for new tables | Low |
| `app/schemas/` | Pydantic schemas for new models | Low |
| `app/api/v1/` | Endpoints for treatment CRUD (optional) | Medium |
| Database views | Create Esri-compatible views (SQL) | Medium |

### 7.3 Esri Configuration

| Task | Complexity |
|------|------------|
| Register PostgreSQL DB with ArcGIS Enterprise | Medium (APSU likely already done) |
| Create Feature Services from views | Low-Medium |
| Configure relationships (infestations → treatments) | Medium |
| Set up Field Maps for data collection | Medium |
| Create ArcGIS Dashboard | Low-Medium |

**Overall Complexity Estimate:** Medium — requires schema additions and Esri configuration, but no major rewrite of Invasive Trace's core ML pipeline.

---

## 8. Risk Assessment

### 8.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Esri PostGIS conflicts** | Medium | High | Use separate schemas; test in dev first |
| **Geometry type mismatch** | Low | Medium | Explicit SRID casting (always EPSG:4326) |
| **Performance degradation** | Low | Medium | Index views; monitor query plans |
| **Versioning complexity** | Medium | Medium | Start with non-versioned; add later if needed |
| **Data sync issues** | Low | High | Use DB triggers or application-level sync |

### 8.2 Organizational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **User resistance to dual systems** | Medium | Medium | Clear communication; phased rollout |
| **Maintenance burden** | High | Medium | Document thoroughly; automate where possible |
| **Esri licensing costs** | Low | High | Already covered by APSU GIS Center |
| **Skill gap (FastAPI + Esri)** | Medium | Medium | Training; leverage existing Esri expertise |

### 8.3 Data Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Field data overwriting predictions** | Low | High | Read-only views for predictions; separate tables for edits |
| **Species name inconsistencies** | Medium | Medium | Add `species_taxonomy` reference table |
| **Attachment storage (photos)** | Medium | Low | Use Esri's attachment framework; store in `gdb_items` |

---

## 9. Alternative Approaches Considered

### 9.1 Use Esri's Python API (ArcGIS API for Python)
- **Concept:** Invasive Trace pushes predictions to ArcGIS Online/Enterprise via Esri's Python API
- **Pros:** No database-level integration; cloud-native
- **Cons:** Requires ArcGIS Online subscription; less control; API rate limits
- **Verdict:** ⚠️ Possible for cloud-first approach, but APSU uses on-prem Enterprise

### 9.2 Build Custom ArcGIS Web AppBuilder Widget
- **Concept:** Custom widget that calls Invasive Trace API directly
- **Pros:** Seamless integration within ArcGIS web apps
- **Cons:** Requires Dojo/JavaScript expertise; Web AppBuilder is legacy
- **Verdict:** ❌ Not recommended — Web AppBuilder deprecated in favor of Experience Builder

### 9.3 Use ArcGIS Experience Builder + Custom Data Source
- **Concept:** Experience Builder with Invasive Trace as a custom data source
- **Pros:** Modern Esri framework; custom integration possible
- **Cons:** Significant development effort; requires JavaScript/TypeScript
- **Verdict:** ⚠️ Viable but overkill for initial integration

### 9.4 OGC API Features Standard
- **Concept:** Expose Invasive Trace as OGC API Features (standardized geospatial API)
- **Pros:** Industry standard; Esri has partial support
- **Cons:** Esri's support is incomplete; additional middleware needed
- **Verdict:** ⚠️ Future-proofing option, but not immediately practical

---

## 10. Final Recommendations

### 10.1 Strategic Recommendation
**Adopt a Hybrid Integration Approach** — Keep Invasive Trace's AI/ML backend intact while exposing its predictions to APSU's Esri ecosystem via database views and Feature Services.

### 10.2 Phased Implementation Plan

#### Phase 1: Foundation (Weeks 1-2)
1. Create `species_taxonomy` reference table
2. Create `treatment_areas` table (Esri requirement)
3. Create database views in `invasive_trace_esri` schema:
   - `infestation_points_view` (from `invasion_predictions`)
   - `survey_areas_view` (from `regions_of_interest`)
   - `treatment_areas_view` (from `treatment_areas`)
4. Register views with ArcGIS Enterprise as Feature Services

#### Phase 2: Field Workflow (Weeks 3-4)
1. Configure ArcGIS Field Maps for treatment data collection
2. Set up relationships: Infestations → Treatments
3. Test field data collection workflow

#### Phase 3: Visualization (Weeks 5-6)
1. Create ArcGIS Dashboard showing:
   - Invasive Trace predictions (from Feature Service)
   - Treatment progress (from Field Maps)
   - Spectral time series summary (from Invasive Trace API)
2. Configure sharing/permissions for APSU GIS Center staff

#### Phase 4: Feedback Loop (Weeks 7-8, Optional)
1. Implement PATCH endpoint for Esri to update `validated` status
2. Add webhook from Esri to Invasive Trace (when treatment complete → trigger retraining check)
3. Document cross-system workflows

### 10.3 Key Success Metrics
- ✅ Invasive Trace predictions visible in ArcGIS Pro/Portal within 2 weeks
- ✅ Field staff can collect treatment data via ArcGIS Field Maps within 4 weeks
- ✅ Dashboard shows integrated view (predictions + treatments) within 6 weeks
- ✅ Zero disruption to Invasive Trace's ML pipeline throughout integration

### 10.4 Critical Success Factors
1. **Separate schemas** — Never let Esri tools modify Invasive Trace's core tables
2. **Database views** — Use read-only views for Esri exposure; separate tables for edits
3. **Phased rollout** — Start with read-only exposure; add editing later
4. **Documentation** — Update `AGENTS.md` with Esri integration architecture
5. **Testing** — Validate geometry types, SRID, and relationship classes in dev first

---

## 11. Next Steps if Proceeding

1. **Stakeholder Alignment:** Present this evaluation to APSU GIS Center leadership
2. **Technical Spike:** Create a proof-of-concept database view and register it with their ArcGIS Enterprise
3. **Schema Migration:** Author Alembic migration for `treatment_areas` and `species_taxonomy` tables
4. **View Creation:** Write SQL scripts for Esri-compatible views
5. **Esri Configuration:** Work with APSU GIS staff to register Feature Services
6. **Update Documentation:** Add Section 10 to `AGENTS.md` ("Esri Integration Architecture")
7. **Create Spec:** Author `specs/011-esri-integration/spec.md` with detailed requirements

---

## 12. Native App Development Path (ArcGIS Maps SDKs for .NET/Qt)

### 12.1 Overview
Esri's ArcGIS Maps SDKs for Native Apps (.NET SDK, Qt SDK) enable building custom mobile/desktop applications that consume Invasive Trace APIs directly, as an alternative to using ArcGIS Field Maps.

### 12.2 Key Capabilities
- **Direct API Consumption:** Call Invasive Trace FastAPI endpoints (e.g., `/api/v1/predictions`, `/api/v1/rois`) to fetch GeoJSON and render as native map layers.
- **Custom Workflows:** Tailor UI/UX to Invasive Trace-specific features like `hotspot_score` display, `model_version` filtering, and HITL validation integration.
- **Offline Support:** .NET/Qt SDKs offer offline map caching and data editing, useful for field work in remote areas.
- **Cross-Platform:** .NET SDK supports Windows/iOS/Android; Qt SDK supports Windows/macOS/Linux/mobile.

### 12.3 Pros/Cons vs. Field Maps
| Aspect | Custom Native App (.NET/Qt) | ArcGIS Field Maps |
|--------|-----------------------------|------------------|
| **Development Effort** | High (requires .NET/Qt expertise) | Low (out-of-the-box) |
| **Customization** | Full control over UI/UX and workflows | Limited to Field Maps configuration |
| **API Integration** | Direct consumption of Invasive Trace REST endpoints | Limited to Esri Feature Services |
| **Offline Capabilities** | Advanced offline map/data editing | Basic offline support |
| **Maintenance** | High (app updates, OS compatibility) | Low (managed by Esri) |
| **Attachments/Versioning** | Requires custom implementation | Built-in support |

### 12.4 When to Choose Native Apps
- Field Maps lacks required offline workflows or custom UI for Invasive Trace-specific features.
- Need deep integration with Invasive Trace's ML outputs (e.g., displaying `hotspot_score` heatmaps, filtering by `model_version`).
- Organization has existing .NET/Qt development resources.

**Verdict:** ⚠️ Use only if Field Maps cannot meet specialized workflow requirements. High effort with limited added value for standard invasive species management.

---

## 13. Experience Builder vs. Pre-built Invasive Vegetation Management Solution

### 13.1 Pre-built Invasive Vegetation Management Solution
- **Overview:** Esri's out-of-the-box solution with pre-configured workflows for survey, treatment, and monitoring.
- **Pros:** Fast setup (register Feature Services), no coding required, aligns with Esri best practices.
- **Cons:** Limited customization, cannot directly consume Invasive Trace REST APIs (only Esri Feature Services).

### 13.2 ArcGIS Experience Builder
- **Overview:** Low-code builder for custom web applications with drag-and-drop widgets and custom JavaScript/TypeScript extensions.
- **Customization Capabilities:**
  - Custom widgets to call Invasive Trace FastAPI endpoints and render GeoJSON as map layers.
  - Embed Invasive Trace's HITL validation UI directly into the Experience Builder app.
  - Combine Esri Feature Services (treatments, surveys) with Invasive Trace API data in a single dashboard.
- **Integration Effort:** Medium (build custom widgets to bridge Invasive Trace APIs and Experience Builder).
- **Pros:** Balance of low-code speed and custom integration capability.
- **Cons:** Requires JavaScript/TypeScript expertise for custom widgets.

### 13.3 Comparison Matrix
| Feature | Pre-built Solution | Experience Builder |
|---------|--------------------|--------------------|
| **Setup Time** | Days | Weeks (with custom widgets) |
| **Customization** | Low | Medium-High |
| **Invasive Trace API Integration** | No (only Feature Services) | Yes (via custom widgets) |
| **Workflow Alignment** | Standard invasive vegetation workflows | Custom workflows possible |
| **Development Skill** | Esri configuration | JavaScript + Esri Experience Builder |

### 13.4 When to Use Which
- **Pre-built Solution:** For standard invasive species workflows where Invasive Trace data is exposed via Esri Feature Services (no custom API integration needed).
- **Experience Builder:** When need to integrate Invasive Trace REST APIs directly, or customize UI beyond what pre-built offers.

**Verdict:** ✅ Start with pre-built solution for fast rollout; upgrade to Experience Builder with custom widgets if API integration is required.

---

## 14. ArcGIS Dashboards Enhancement for ML Predictions

### 14.1 Visualization Strategy
ArcGIS Dashboards provide real-time visualization of Invasive Trace ML predictions and KPIs, complementing the existing HITL dashboard.

### 14.2 Displaying Invasive Trace ML Predictions
- **Data Source:** `invasive_trace_esri.infestation_points` Feature Service (maps to `invasion_predictions` table).
- **Symbology:**
  - Color-code by `species_label` (e.g., *Bromus tectorum* = red, *Toxicodendron radicans* = orange).
  - Size by `hotspot_score` (higher score = larger point).
  - Opacity by `confidence` (higher confidence = more opaque).
- **Filtering:** Add dashboard filters for `model_version`, `validated` status, and `predicted_at` date range.

### 14.3 Real-Time KPIs
| KPI | Data Source | Calculation |
|-----|-------------|-------------|
| **Invasion Spread Rate** | `invasion_predictions` | Count of new predictions per week/month |
| **Treatment Progress** | `treatment_areas` (Esri) | % of infestations with `TreatmentStatus = Treated` |
| **Model Confidence** | `invasion_predictions` | Average `confidence` score across all predictions |
| **Pending Reviews** | `invasion_predictions` | Count of predictions where `validated IS NULL` |
| **Species Distribution** | `invasion_predictions` | Count of predictions per `species_label` |

### 14.4 Integration with Existing HITL Dashboard
- **Embed ArcGIS Dashboard:** Use an iframe to embed the ArcGIS Dashboard into Invasive Trace's existing Leaflet-based HITL dashboard (`GET /`).
- **Embed Invasive Trace Metrics:** Call Invasive Trace's `/api/v1/metrics` endpoint to display model performance KPIs (e.g., F1 score, precision) in the ArcGIS Dashboard via custom widgets.
- **Cross-Linking:** Add links from ArcGIS Dashboard prediction points to Invasive Trace's validation endpoint (`PATCH /api/v1/predictions/{id}/validate`).

**Verdict:** ✅ High value-add — extends Invasive Trace's HITL dashboard with Esri's mature visualization and KPI tools.

---

## 15. JavaScript SDK Custom Web App Evaluation

### 15.1 Overview
Build a fully custom web mapping application using the ArcGIS Maps SDK for JavaScript, consuming Invasive Trace FastAPI endpoints directly.

### 15.2 Key Features
- **Direct API Consumption:** Fetch GeoJSON from Invasive Trace endpoints (`/api/v1/predictions`, `/api/v1/rois`) and add as `GeoJSONLayer` or `FeatureLayer` to the map.
- **Custom UI/UX:** Design a tailored interface that integrates:
  - Invasive Trace's HITL validation form (`PATCH /api/v1/predictions/{id}/validate`)
  - Model metrics from `/api/v1/metrics`
  - Spectral time series charts from `spectral_time_series` data
- **Seamless Integration:** No Esri template constraints — embed Invasive Trace-specific workflows directly into the map app.

### 15.3 Effort Comparison
| Solution | Development Effort | Skill Required | Customization |
|----------|--------------------|----------------|---------------|
| Pre-built Invasive Vegetation Solution | Low | Esri configuration | Low |
| Experience Builder | Medium | JavaScript + Experience Builder | Medium-High |
| **Custom JavaScript SDK App** | High | ArcGIS JS SDK + Web development | Full |

### 15.4 Pros/Cons
- **Pros:**
  - Full control over UI/UX and workflow integration.
  - No Esri template limitations.
  - Direct, low-latency access to Invasive Trace APIs.
- **Cons:**
  - Highest development effort.
  - Requires specialized ArcGIS JS SDK and web development skills.
  - Longer time-to-production than low-code alternatives.

**Verdict:** ⚠️ Only warranted if Experience Builder cannot meet integration needs. Use for highly custom workflows that require deep Invasive Trace backend integration.

---

## 16. Updated Recommendations (Refined Hybrid Approach)

### 16.1 Revised Strategic Approach
The hybrid integration approach remains the best fit, but is now refined to incorporate the new Esri tools evaluated:

1. **Primary Frontend:** Start with the **pre-built Invasive Vegetation Management solution** for standard workflows (survey, treatment, monitoring) using Esri Feature Services derived from Invasive Trace data.
2. **Enhanced Visualization:** Add **ArcGIS Dashboards** to display ML predictions, KPIs, and treatment progress — embed this into Invasive Trace's existing HITL dashboard.
3. **Custom Integration (If Needed):** Use **ArcGIS Experience Builder** with custom widgets to consume Invasive Trace REST APIs directly, if the pre-built solution lacks required integration.
4. **Specialized Workflows:** Consider a **custom JavaScript SDK app** only if Experience Builder cannot meet deep integration needs (e.g., embedding HITL validation, model metrics).
5. **Native Apps:** Use **.NET/Qt SDKs** to build custom mobile/desktop apps only if ArcGIS Field Maps lacks required offline capabilities or custom workflows.

### 16.2 Decision Matrix
| Requirement | Recommended Esri Tool |
|-------------|-----------------------|
| Standard invasive vegetation workflows | Pre-built Invasive Vegetation Management Solution |
| ML prediction visualization + KPIs | ArcGIS Dashboards |
| Custom integration with Invasive Trace APIs | Experience Builder (custom widgets) |
| Deep workflow customization | Custom JavaScript SDK App |
| Specialized mobile/desktop workflows | .NET/Qt Native Apps |

### 16.3 Updated Phased Implementation Plan
#### Phase 1: Foundation (Weeks 1-2)
- Create `treatment_areas` and `species_taxonomy` tables.
- Create Esri-compatible database views and register as Feature Services.
- Configure pre-built Invasive Vegetation Management solution.

#### Phase 2: Visualization (Weeks 3-4)
- Build ArcGIS Dashboard with ML predictions and KPIs.
- Embed dashboard into Invasive Trace HITL dashboard.

#### Phase 3: Custom Integration (Weeks 5-8, Optional)
- Develop Experience Builder custom widgets to consume Invasive Trace APIs.
- Evaluate need for custom JavaScript SDK app or native apps.

### 16.4 Changes to Original Recommendations
- **Added ArcGIS Dashboards** as a core component of the hybrid approach (previously only mentioned briefly).
- **Clarified Experience Builder vs. pre-built solution** — pre-built is default, Experience Builder for custom integration.
- **Added native app and custom JS app paths** as specialized options, not core recommendations.
- **Reduced emphasis on full replacement or middleware** — hybrid remains the clear choice.

---

## Appendix A: Esri Invasive Vegetation Management Data Model (Expected)

Based on Esri's standard solution pattern, the following fields are typically expected:

**Infestation Points:**
- `GlobalID` (GUID)
- `Species` (text)
- `InfestationStatus` (confirmed/pending/rejected)
- `DetectionDate` (date)
- `Confidence` (float)
- `TreatmentStatus` (treated/untreated)
- `Shape` (point geometry)

**Treatment Areas:**
- `GlobalID` (GUID)
- `InfestationID` (GUID, relates to Infestation Points)
- `TreatmentType` (chemical/mechanical/biological)
- `TreatmentDate` (date)
- `ChemicalUsed` (text, if chemical)
- `AreaTreated` (float, acres)
- `Shape` (polygon geometry)

**Survey Areas:**
- `GlobalID` (GUID)
- `SurveyName` (text)
- `SurveyDate` (date)
- `Surveyor` (text)
- `Shape` (polygon geometry)

---

**Document Version:** 1.0  
**Next Review:** After Phase 1 completion (2 weeks)  
**Distribution:** APSU GIS Center, Southern Grassland Institute, Invasive Trace Dev Team
