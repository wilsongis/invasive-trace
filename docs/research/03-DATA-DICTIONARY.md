# Data Dictionary

## 1. Entities

### `ExampleEntity`
| Field Name | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key | Unique identifier. |
| `name` | String(100) | Not Null | Given name representing the entity. |
| `geom` | Geometry | PostGIS | Geospatial representation of the entity. |

*(Add other tables and fields below)*
