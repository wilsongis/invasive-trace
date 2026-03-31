# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Draft  
**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: Fill in feature-specific edge cases.
  The following are REQUIRED for any feature touching external APIs or raster data.
-->

- What happens when the Planetary Computer returns 0 scenes for the requested ROI + date range?
- What happens when a scene has `cloud_cover > 0.20` (must set `is_masked=TRUE`, exclude from index computation)?
- What happens when an external API returns HTTP 429? (exponential backoff, max 3 retries, then log + skip)
- What happens when a STAC item exists in the catalog but the COG tile is missing or corrupt?
- What happens when `confidence` is computed outside the 0.0–1.0 range?
- [Add feature-specific edge cases below]

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

<!--
  Invasive Trace FR prompts — include whichever apply to this feature:
  - Spatial: geometry SRID 4326, GiST index on new geometry columns
  - API resilience: backoff + skip pattern for Planetary Computer / iNaturalist / EDDMapS
  - Schema integrity: Alembic migration required for new/modified columns
  - ML registry: model_version matches AGENTS.md Section 6 registry entry
  - HITL: validated flag + validator_notes writable via PATCH endpoint
-->

- **FR-001**: System MUST [specific capability]
- **FR-002**: System MUST [specific capability]
- **FR-003**: System MUST [specific capability]
- **FR-004**: System MUST handle HTTP 429 from [external API] with exponential backoff (max 3 retries); log and skip after failure
- **FR-005**: System MUST [data requirement]

*Mark unclear requirements:*

- **FR-006**: [NEEDS CLARIFICATION: describe the ambiguity]

### Key Entities *(include if feature involves data)*

<!--
  Invasive Trace canonical tables (check AGENTS.md Section 4 for DDL before adding columns):
  - regions_of_interest — WGS84 polygons, GiST index
  - invasion_predictions — species_label, confidence (0–1), hotspot_score, model_version, validated
  - ground_truth_observations — source IN ('iNaturalist','EDDMapS','field_survey'), raw_payload JSONB
  - spectral_time_series — ndvi, endvi, red_edge, cloud_cover, is_masked, stac_item
  Only list entities this feature creates or modifies.
-->

- **[Entity]**: [Which canonical table, which columns this feature reads/writes, any new columns requiring migration]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- [Assumption about target users, e.g., "Users have stable internet connectivity"]
- [Assumption about scope boundaries, e.g., "Mobile support is out of scope for v1"]
- [Assumption about data/environment, e.g., "Existing authentication system will be reused"]
- [Dependency on existing system/service, e.g., "Requires access to the existing user profile API"]
