"""ROI request/response schemas and geometry helpers."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from shapely import wkt
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


def _force_2d(geom: BaseGeometry) -> BaseGeometry:
    """Drop Z/M dimensions if present to keep persistence strictly 2D."""
    return transform(lambda x, y, *rest: (x, y), geom)


def _validate_wgs84_bounds(geom: BaseGeometry) -> None:
    """Ensure coordinates fall within EPSG:4326 longitude/latitude ranges."""
    for ring in [geom.exterior, *geom.interiors]:
        for lon, lat in ring.coords:
            if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
                raise ValueError("ROI coordinates must be valid EPSG:4326 lon/lat values")


class ROICreate(BaseModel):
    """Create payload for a new region of interest."""

    name: str = Field(min_length=1)
    description: str | None = None
    geom_wkt: str = Field(min_length=10, description="WKT polygon in EPSG:4326 coordinates")

    @field_validator("geom_wkt")
    @classmethod
    def validate_polygon_wkt(cls, value: str) -> str:
        geom = wkt.loads(value)
        if geom.geom_type != "Polygon":
            raise ValueError("ROI geometry must be a POLYGON WKT")
        if not geom.is_valid:
            raise ValueError("ROI geometry is invalid (check self-intersections)")
        return value


class ROIResponse(BaseModel):
    """Response payload for a persisted region of interest."""

    id: UUID
    name: str
    description: str | None
    geometry: dict
    created_at: datetime
    updated_at: datetime


def parse_wkt_polygon(value: str) -> BaseGeometry:
    """Return a validated Shapely polygon from WKT input."""
    geom = _force_2d(wkt.loads(value))
    if geom.geom_type != "Polygon":
        raise ValueError("ROI geometry must be a POLYGON WKT")
    if not geom.is_valid:
        raise ValueError("ROI geometry is invalid (check self-intersections)")
    _validate_wgs84_bounds(geom)
    return geom


def to_geojson_mapping(geom: BaseGeometry) -> dict:
    """Convert a shapely geometry into a GeoJSON geometry mapping."""
    return mapping(geom)
