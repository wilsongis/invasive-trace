# TODO: Esri Integration (spec 011)

Phased implementation plan for integrating Invasive Trace with the APSU GIS Center's Esri ecosystem.

Based on evaluation at `docs/research/esri-integration-evaluation.md`.

---

## Phase 1: Foundation (Weeks 1-2) — Priority: HIGH

### Database Changes
- [ ] Author `specs/011-esri-integration/spec.md` with detailed requirements and architecture decisions
- [ ] Create `treatment_areas` table migration (0006) — tracks treatment history and outcomes
- [ ] Create `species_taxonomy` table migration (0006) — canonical invasive species reference with APSU local names
- [ ] Build Esri-compatible database views in `invasive_trace_esri` schema:
  - [ ] `v_predictions` — invasion_predictions with WKT geometry for Esri
  - [ ] `v_ground_truth` — ground_truth_observations with validation status
  - [ ] `v_rois` — regions_of_interest with area calculations
  - [ ] `v_spectral_indices` — spectral_time_series with computed indices
  - [ ] `v_treatment_areas` — treatment_areas with status and effectiveness metrics
- [ ] Register views as ArcGIS Feature Services via ArcGIS Server/Enterprise

### Estimated Effort: 2-3 days

---

## Phase 2: Visualization (Weeks 3-4) — Priority: HIGH

### ArcGIS Dashboards
- [ ] Configure ArcGIS Dashboard with Invasive Trace KPIs:
  - [ ] Total predictions count with confidence distribution
  - [ ] Hotspot score distribution (Stage 3 output)
  - [ ] Validation status pie chart (pending/confirmed/rejected)
  - [ ] Species breakdown bar chart
- [ ] Add ML prediction layer with hotspot scoring visualization
- [ ] Configure popups with prediction metadata (model_version, confidence, hotspot_score)
- [ ] Add time-series chart for spectral indices per ROI
- [ ] Set up dashboard filters by species, ROI, validation status, date range

### Estimated Effort: 3-4 days

---

## Phase 3: Field Workflow (Weeks 5-6) — Priority: HIGH

### Invasive Vegetation Management Solution
- [ ] Deploy Esri's Invasive Vegetation Management solution to AGOL/Enterprise
- [ ] Configure solution to consume Invasive Trace Feature Services
- [ ] Set up field verification workflow:
  - [ ] Sync pending predictions to Field Maps/Solution
  - [ ] Configure verification forms with species confirmation, treatment options
  - [ ] Set up photo attachment support for field evidence
- [ ] Implement callback/webhook from Esri to Invasive Trace `PATCH /api/v1/predictions/{id}/validate`
- [ ] Test end-to-end: Prediction → Field Verification → Validation Update

### Estimated Effort: 4-5 days

---

## Phase 4: Custom Integration (Weeks 7-8, Optional) — Priority: LOW

### Experience Builder (Optional)
- [ ] Evaluate need for custom Experience Builder widgets
- [ ] Build custom API integration widget if needed:
  - [ ] Direct Invasive Trace API consumption
  - [ ] Hybrid dashboard combining Esri + Invasive Trace data
- [ ] Set up automated sync jobs (database → Feature Services refresh)

### Estimated Effort: 3-5 days (if needed)

---

## Cross-Cutting Concerns

### Documentation
- [ ] Update `AGENTS.md` Section 10 with Esri Integration Architecture
- [ ] Update `README.md` with Esri Integration section
- [ ] Create `specs/011-esri-integration/` with full design artifacts:
  - [ ] `spec.md` — requirements and acceptance criteria
  - [ ] `plan.md` — implementation plan
  - [ ] `tasks.md` — executable task list
  - [ ] `data-model.md` — schema changes and view definitions
  - [ ] `quickstart.md` — end-to-end validation flow

### Testing
- [ ] Unit tests for new ORM models (`treatment_areas`, `species_taxonomy`)
- [ ] Integration tests for database views
- [ ] End-to-end test: Invasive Trace prediction → Esri Dashboard display
- [ ] End-to-end test: Field verification → Invasive Trace validation update

### Configuration
- [ ] Add Esri connection parameters to `app/config.py`:
  - [ ] `ESRI_PORTAL_URL`
  - [ ] `ESRI_FEATURE_SERVICE_URL`
  - [ ] `ESRI_WEBHOOK_SECRET`
- [ ] Document environment variables in `.env.example`

---

## Success Metrics

- [ ] ArcGIS Dashboard displays 100% of Invasive Trace predictions with hotspot scores
- [ ] Field verification workflow processes predictions with <5 min latency
- [ ] Webhook callback successfully validates predictions in Invasive Trace
- [ ] Zero direct modifications to Invasive Trace tables by Esri (read-only views enforced)
- [ ] APSU GIS team can access dashboards without Invasive Trace credentials

---

## Risks & Mitigations

| Risk | Mitigation |
|:---|:---|
| Esri schema changes break views | Versioned views with migration scripts |
| Webhook security compromise | HMAC signature validation on callbacks |
| Feature Service rate limits | Implement retry with exponential backoff |
| Dual-write data inconsistency | Single source of truth: Invasive Trace DB; Esri is read-only |
