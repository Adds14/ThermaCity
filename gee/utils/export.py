"""
ThermaCity — GEE Export & Reduction Utilities

Provides the SINGLE canonical reduction and export pattern used by
every extraction script. This guarantees mathematical consistency:
all bands are reduced to the same grid, with the same reducer,
at the same scale and CRS.

Core contract:
  - Reducer:  ee.Reducer.mean()
  - Scale:    500 meters
  - CRS:      EPSG:4326
  - Grid:     The shared FeatureCollection from geometry.get_analysis_grid()

Usage:
    from utils.export import reduce_to_grid, export_to_local_csv

    reduced = reduce_to_grid(composite, grid, output_name="lst")
    export_to_local_csv(reduced, "lst_2023", out_dir="exports", selectors=["cell_code", "lst"])
"""

import logging
import urllib.request
from pathlib import Path

import ee

logger = logging.getLogger(__name__)

# ── Pipeline Constants (shared across ALL extraction scripts) ─
REDUCE_SCALE = 500          # meters — matches grid cell size
REDUCE_CRS = "EPSG:4326"   # WGS84

HOT_SEASON_START_MONTH = 3  # March
HOT_SEASON_END_MONTH = 6    # June (inclusive)

DEFAULT_YEARS = list(range(2021, 2027))  # 2021–2026

# ══════════════════════════════════════════════════════════════
# Canonical Reduction
# ══════════════════════════════════════════════════════════════


def reduce_to_grid(
    image: ee.Image,
    grid: ee.FeatureCollection,
    output_name: str | None = None,
) -> ee.FeatureCollection:
    """
    Reduce an image to grid-cell means using ee.Reducer.mean().
    """
    reduced = image.reduceRegions(
        collection=grid,
        reducer=ee.Reducer.mean(),
        scale=REDUCE_SCALE,
        crs=REDUCE_CRS,
    )

    if output_name:
        reduced = reduced.map(
            lambda f: f.set(output_name, f.get("mean"))
        )

    return reduced


# ══════════════════════════════════════════════════════════════
# Local Export (Synchronous)
# ══════════════════════════════════════════════════════════════


def export_to_local_csv(
    feature_collection: ee.FeatureCollection,
    description: str,
    out_dir: str,
    selectors: list[str] | None = None,
) -> Path:
    """
    Download a FeatureCollection directly as a CSV to the local disk.
    This bypasses Google Drive entirely by using getDownloadURL().
    NOTE: This is limited by GEE's 10MB payload and processing timeout limits,
    which is why we use a 500m grid for local synchronous downloading.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    file_path = out_path / f"{description}.csv"
    
    logger.info(f"  Generating download URL for {description}...")
    
    # Request the download URL from GEE servers
    try:
        url = feature_collection.getDownloadURL(
            filetype="CSV",
            selectors=selectors,
            filename=description
        )
    except Exception as e:
        logger.error(f"Failed to generate URL for {description}: {e}")
        raise

    logger.info(f"  Downloading from URL -> {file_path}")
    urllib.request.urlretrieve(url, file_path)
    logger.info(f"  ✓ Saved {file_path.name}")
    
    return file_path


# ══════════════════════════════════════════════════════════════
# Date Helpers
# ══════════════════════════════════════════════════════════════


def hot_season_date_range(year: int) -> tuple[str, str]:
    return (
        f"{year}-{HOT_SEASON_START_MONTH:02d}-01",
        f"{year}-{HOT_SEASON_END_MONTH:02d}-30",
    )
