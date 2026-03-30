"""Unit tests for ROI schema validation and geometry conversion."""

import pytest

from app.schemas.roi import ROICreate, parse_wkt_polygon, to_geojson_mapping


def test_roi_create_accepts_valid_polygon_wkt() -> None:
    payload = ROICreate(
        name="Test ROI",
        description="desc",
        geom_wkt="POLYGON((-100 40, -99 40, -99 39, -100 39, -100 40))",
    )
    assert payload.name == "Test ROI"


def test_roi_create_rejects_non_polygon() -> None:
    with pytest.raises(ValueError):
        ROICreate(name="Bad", geom_wkt="POINT(-100 40)")


def test_roi_create_rejects_invalid_polygon() -> None:
    with pytest.raises(ValueError):
        ROICreate(
            name="Bad",
            geom_wkt="POLYGON((0 0, 2 2, 2 0, 0 2, 0 0))",
        )


def test_wkt_to_geojson_round_trip() -> None:
    poly = parse_wkt_polygon("POLYGON((-100 40, -99 40, -99 39, -100 39, -100 40))")
    geojson = to_geojson_mapping(poly)
    assert geojson["type"] == "Polygon"
    assert len(geojson["coordinates"][0]) == 5
