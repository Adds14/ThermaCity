"""
ThermaCity — Geometry & Grid Utilities

Handles:
  1. Loading the Pune city boundary polygon (GeoJSON → ee.Geometry)
  2. Generating the 100×100 m analysis grid (shapely → GeoJSON → ee.FeatureCollection)

The grid is the foundational spatial unit. EVERY extraction script uses
the same grid via `get_analysis_grid()` to guarantee cell-level alignment
across all feature layers.

Grid Specification:
  - Cell size: ~100 m × ~100 m (adjusted for latitude)
  - CRS: EPSG:4326 (WGS84)
  - Cell codes: "PUNE_R{row:04d}_C{col:04d}"
  - Cells are clipped to the Pune boundary polygon

Usage:
    from utils.geometry import load_pune_boundary_ee, get_analysis_grid

    aoi = load_pune_boundary_ee()
    grid = get_analysis_grid()  # ~30,000+ cells as ee.FeatureCollection
"""

import json
import logging
import math
from pathlib import Path

import ee
from shapely.geometry import box, mapping, shape
from shapely.prepared import prep

logger = logging.getLogger(__name__)

# ── Path Constants ────────────────────────────────────────────
_BASE_DIR = Path(__file__).resolve().parent.parent
BOUNDARY_PATH = _BASE_DIR / "boundaries" / "pune_boundary.geojson"
GRID_PATH = _BASE_DIR / "boundaries" / "pune_grid.geojson"

# ── Grid Parameters ──────────────────────────────────────────
CELL_SIZE_M = 100
PUNE_LATITUDE = 18.52  # Central latitude for degree conversion

# 1 degree of latitude ≈ 111,320 m (constant globally)
# 1 degree of longitude ≈ 111,320 × cos(lat) m (varies with latitude)
_LAT_DEG_PER_METER = 1.0 / 111_320
_LNG_DEG_PER_METER = 1.0 / (111_320 * math.cos(math.radians(PUNE_LATITUDE)))

# Cell dimensions in degrees (≈ 100 m on the ground at Pune's latitude)
CELL_LAT_DEG = CELL_SIZE_M * _LAT_DEG_PER_METER  # ≈ 0.000898°
CELL_LNG_DEG = CELL_SIZE_M * _LNG_DEG_PER_METER  # ≈ 0.000947°


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


# ══════════════════════════════════════════════════════════════
# Grid Generation
# ══════════════════════════════════════════════════════════════


def generate_grid(force: bool = False) -> Path:
    """
    Generate the 100×100 m analysis grid and save as GeoJSON.

    Creates rectangular cells covering the Pune boundary. Each cell
    is ~100 m × ~100 m on the ground, assigned a unique cell_code
    in the format "PUNE_R{row}_C{col}".

    Args:
        force: If True, regenerate even if the file already exists.

    Returns:
        Path to the saved GeoJSON file.
    """
    if GRID_PATH.exists() and not force:
        logger.info(f"Grid already exists at {GRID_PATH}. Use force=True to regenerate.")
        return GRID_PATH

    logger.info("Generating 100×100 m analysis grid for Pune...")

    # Load boundary and prepare for fast intersection tests
    boundary = load_pune_boundary_shapely()
    boundary_prepared = prep(boundary)
    min_lng, min_lat, max_lng, max_lat = boundary.bounds

    logger.info(
        f"  Boundary bbox: "
        f"lng=[{min_lng:.4f}, {max_lng:.4f}], "
        f"lat=[{min_lat:.4f}, {max_lat:.4f}]"
    )
    logger.info(
        f"  Cell size: {CELL_LAT_DEG:.6f}° lat × {CELL_LNG_DEG:.6f}° lng "
        f"(≈ {CELL_SIZE_M}m × {CELL_SIZE_M}m)"
    )

    features = []
    row = 0
    lat = min_lat

    while lat < max_lat:
        col = 0
        lng = min_lng

        while lng < max_lng:
            # Create cell rectangle
            cell = box(lng, lat, lng + CELL_LNG_DEG, lat + CELL_LAT_DEG)

            # Keep only cells that intersect the city boundary
            if boundary_prepared.intersects(cell):
                cell_code = f"PUNE_R{row:04d}_C{col:04d}"
                centroid = cell.centroid

                features.append({
                    "type": "Feature",
                    "geometry": mapping(cell),
                    "properties": {
                        "cell_code": cell_code,
                        "row": row,
                        "col": col,
                        "centroid_lat": round(centroid.y, 6),
                        "centroid_lng": round(centroid.x, 6),
                    },
                })

            lng += CELL_LNG_DEG
            col += 1

        lat += CELL_LAT_DEG
        row += 1

        # Progress logging every 50 rows
        if row % 50 == 0:
            logger.info(f"  Processed row {row}... ({len(features)} cells so far)")

    logger.info(f"  Grid complete: {len(features)} cells in {row} rows")

    # Save as GeoJSON
    grid_geojson = {
        "type": "FeatureCollection",
        "name": "ThermaCity Analysis Grid",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::4326"},
        },
        "metadata": {
            "cell_size_m": CELL_SIZE_M,
            "cell_lat_deg": CELL_LAT_DEG,
            "cell_lng_deg": CELL_LNG_DEG,
            "total_cells": len(features),
            "total_rows": row,
            "pune_latitude": PUNE_LATITUDE,
        },
        "features": features,
    }

    GRID_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GRID_PATH, "w", encoding="utf-8") as f:
        # Compact JSON to keep filesize manageable (~8-12 MB for ~30k cells)
        json.dump(grid_geojson, f, separators=(",", ":"))

    file_size_mb = GRID_PATH.stat().st_size / (1024 * 1024)
    logger.info(f"  Saved grid to {GRID_PATH} ({file_size_mb:.1f} MB)")

    return GRID_PATH


# ══════════════════════════════════════════════════════════════
# Grid Loading (for GEE scripts)
# ══════════════════════════════════════════════════════════════


def get_analysis_grid(asset_id: str | None = None) -> ee.FeatureCollection:
    """
    Load the 100×100 m analysis grid as an ee.FeatureCollection.

    This is THE canonical function that all extraction scripts must use
    to ensure spatial alignment. Every pixel reduction hits the same
    set of grid polygons.

    Args:
        asset_id: Optional GEE asset ID (e.g., 'projects/my-project/assets/thermacity_grid').
                  If provided, loads from GEE asset (faster for repeated runs).
                  If None, loads from local GeoJSON file.

    Returns:
        ee.FeatureCollection with properties: cell_code, row, col,
        centroid_lat, centroid_lng.
    """
    # ── Option A: Load from GEE asset (recommended for production) ──
    if asset_id:
        logger.info(f"Loading grid from GEE asset: {asset_id}")
        return ee.FeatureCollection(asset_id)

    # ── Option B: Load from local GeoJSON ──
    if not GRID_PATH.exists():
        logger.info("Grid file not found. Generating grid first...")
        generate_grid()

    logger.info(f"Loading grid from local file: {GRID_PATH}")
    with open(GRID_PATH, encoding="utf-8") as f:
        grid_geojson = json.load(f)

    total = len(grid_geojson["features"])
    logger.info(f"  Loaded {total} grid cells. Converting to ee.FeatureCollection...")

    # Convert entire GeoJSON to ee.FeatureCollection in one call
    # (more efficient than creating individual ee.Feature objects)
    grid_fc = ee.FeatureCollection(grid_geojson["features"])

    logger.info(f"  ee.FeatureCollection created ({total} features).")
    return grid_fc


# ══════════════════════════════════════════════════════════════
# CLI Entry Point (generate grid standalone)
# ══════════════════════════════════════════════════════════════


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
    )
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate the ThermaCity 100×100 m analysis grid for Pune."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Regenerate grid even if it already exists.",
    )
    args = parser.parse_args()

    path = generate_grid(force=args.force)
    print(f"\nGrid saved to: {path}")
