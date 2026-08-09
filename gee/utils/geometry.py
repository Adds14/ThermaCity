"""
ThermaCity — Geometry & Grid Utilities

Handles:
  1. Loading the Pune city boundary polygon (GeoJSON → ee.Geometry)

Usage:
    from utils.geometry import load_pune_boundary_ee

    aoi = load_pune_boundary_ee()
"""

import json
import logging
from pathlib import Path
import ee
from shapely.geometry import shape

logger = logging.getLogger(__name__)

# ── Path Constants ────────────────────────────────────────────
_BASE_DIR = Path(__file__).resolve().parent.parent
BOUNDARY_PATH = _BASE_DIR / "boundaries" / "pune_boundary.geojson"

# ══════════════════════════════════════════════════════════════
# Boundary Loading
# ══════════════════════════════════════════════════════════════

def load_pune_boundary_geojson() -> dict:
    """Load the raw Pune boundary GeoJSON as a Python dict."""
    if not BOUNDARY_PATH.exists():
        raise FileNotFoundError(
            f"Pune boundary file not found: {BOUNDARY_PATH}\n"
            "Download from DataMeet: https://github.com/datameet/Municipal_Spatial_Data"
        )
    with open(BOUNDARY_PATH, encoding="utf-8") as f:
        return json.load(f)

def load_pune_boundary_shapely():
    """Load the Pune boundary as a shapely geometry."""
    geojson = load_pune_boundary_geojson()
    feature = geojson["features"][0]
    return shape(feature["geometry"])

def load_pune_boundary_ee() -> ee.Geometry:
    """
    Load the Pune boundary as an ee.Geometry for GEE operations.

    Returns:
        ee.Geometry.Polygon in EPSG:4326
    """
    geojson = load_pune_boundary_geojson()
    feature = geojson["features"][0]
    return ee.Geometry(feature["geometry"])
