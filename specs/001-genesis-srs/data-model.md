# Data Model: 001-genesis-srs

The baseline SRS focuses on architectural scaffolding rather than business-specific database tables. The primary "entities" managed in this phase are contextual and foundational.

## 1. The Context Entity (`AGENTS.md`)
While not a database table, this is the most critical state object in the system.

**Attributes:**
- `Objective`: String (The current goal of the developer/agent)
- `Status`: String (e.g., Verified, In Progress)
- `Notebook ID`: String (UUID mapping to the AntiGravity MCP)
- `Tasks`: Boolean Array (Checklist of pending/completed objectives)

**Relationships:**
- Dictates constraints to `.specify/memory/constitution.md`
- Governs the execution scope of all tools.

## 2. Spatial Base Model (PostGIS Scaffolding)
To prepare for future spatial data, the application will require a base SQLAlchemy model configured for PostGIS.

**Attributes (Base):**
- `id`: UUID (Primary Key)
- `created_at`: DateTime
- `updated_at`: DateTime
- `geom`: Geometry (PostGIS extension required)

**Relationships:**
- Forms the base class from which future domain-specific geographical entities will inherit.
