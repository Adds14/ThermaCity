"""
ThermaCity — GeoJSON Builder Service

Converts SQLAlchemy result rows that carry PostGIS geometries (WKB or
WKT) into RFC 7946-compliant GeoJSON FeatureCollection dicts, ready
to be serialised and returned by the API.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import shapely.wkb
import shapely.wkt
from geoalchemy2 import WKBElement, WKTElement
from shapely.geometry import mapping as shapely_mapping

logger = logging.getLogger(__name__)


def build_feature_collection(
    rows: list[Any],
    geometry_column: str = "geom",
) -> dict[str, Any]:
    """Build a GeoJSON FeatureCollection from SQLAlchemy result rows.

    Parameters
    ----------
    rows : list
        SQLAlchemy ORM instances **or** ``Row`` / ``RowMapping`` objects
        that contain a geometry attribute/column.  Every non-geometry
        column is included in the feature's ``properties``.
    geometry_column : str
        Name of the column/attribute that holds the PostGIS geometry
        (``WKBElement``, ``WKTElement``, hex-encoded WKB string, or WKT
        string).

    Returns
    -------
    dict
        A GeoJSON ``FeatureCollection`` dict::

            {
                "type": "FeatureCollection",
                "features": [ … ]
            }
    """
    features: list[dict[str, Any]] = []

    for row in rows:
        try:
            raw_geom, properties = _extract(row, geometry_column)
            geojson_geom = _to_geojson_geometry(raw_geom)
            features.append(
                {
                    "type": "Feature",
                    "geometry": geojson_geom,
                    "properties": properties,
                }
            )
        except Exception:
            logger.warning(
                "Skipping row — failed to convert geometry.",
                exc_info=True,
            )

    logger.info(
        "Built FeatureCollection with %d features (from %d rows).",
        len(features),
        len(rows),
    )

    return {
        "type": "FeatureCollection",
        "features": features,
    }


# ── internal helpers ──────────────────────────────────────────


def _extract(
    row: Any, geometry_column: str
) -> tuple[Any, dict[str, Any]]:
    """Separate the geometry value from all other columns.

    Handles both ORM model instances (``__dict__``) and Core ``Row``
    objects (``_mapping``).
    """
    # ORM model instances
    if hasattr(row, "__dict__"):
        data = {
            k: v
            for k, v in row.__dict__.items()
            if not k.startswith("_")
        }
    # Core Row / RowMapping objects
    elif hasattr(row, "_mapping"):
        data = dict(row._mapping)
    else:
        data = dict(row)

    raw_geom = data.pop(geometry_column, None)
    if raw_geom is None:
        raise ValueError(
            f"Row has no geometry column '{geometry_column}': {list(data.keys())}"
        )

    # Strip non-serialisable leftovers (e.g. SQLAlchemy InstanceState)
    properties: dict[str, Any] = {}
    for key, value in data.items():
        try:
            json.dumps(value, default=str)
            properties[key] = value
        except (TypeError, ValueError):
            properties[key] = str(value)

    return raw_geom, properties


def _to_geojson_geometry(raw: Any) -> dict[str, Any]:
    """Convert a GeoAlchemy2 / raw geometry value to a GeoJSON dict.

    Supported inputs
    ~~~~~~~~~~~~~~~~
    * ``geoalchemy2.WKBElement``
    * ``geoalchemy2.WKTElement``
    * ``bytes`` — raw WKB
    * ``str``   — hex-encoded WKB **or** WKT string
    """
    if isinstance(raw, WKBElement):
        # WKBElement.data can be memoryview, bytes, or hex-str
        shapely_geom = shapely.wkb.loads(bytes(raw.data), hex=False)
    elif isinstance(raw, WKTElement):
        shapely_geom = shapely.wkt.loads(raw.data)
    elif isinstance(raw, (bytes, memoryview)):
        shapely_geom = shapely.wkb.loads(bytes(raw), hex=False)
    elif isinstance(raw, str):
        # Try hex-encoded WKB first, fall back to WKT
        try:
            shapely_geom = shapely.wkb.loads(raw, hex=True)
        except Exception:
            shapely_geom = shapely.wkt.loads(raw)
    else:
        raise TypeError(
            f"Unsupported geometry type: {type(raw).__name__}"
        )

    return shapely_mapping(shapely_geom)
