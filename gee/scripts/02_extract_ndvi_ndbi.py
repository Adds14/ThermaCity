#!/usr/bin/env python3
"""
ThermaCity — 02: Sentinel-2 Spectral Index Extraction (NDVI, NDBI, NDWI)

Extracts three vegetation/urban/water indices from Sentinel-2 L2A
(Surface Reflectance, harmonized) imagery.

Indices Computed:
  - NDVI = (B8 − B4) / (B8 + B4)   → Vegetation health & greenness
  - NDBI = (B11 − B8) / (B11 + B8) → Built-up / impervious surface density
  - NDWI = (B3 − B8) / (B3 + B8)   → Proximity to water bodies

Processing Chain:
  1. Load Sentinel-2 L2A Harmonized collection
  2. Filter to Pune AOI and hot season (March–June)
  3. Mask opaque clouds and cirrus using QA60 bitmask
  4. Compute normalized difference indices
  5. Compute median composite per hot season
  6. Reduce all 3 bands to 100×100 m grid via ee.Reducer.mean()
  7. Export to Google Drive as CSV

Output Columns:
  - cell_code: Grid cell identifier
  - ndvi:      Normalized Difference Vegetation Index (-1 to 1)
  - ndbi:      Normalized Difference Built-up Index (-1 to 1)
  - ndwi:      Normalized Difference Water Index (-1 to 1)

Usage:
    python 02_extract_ndvi_ndbi.py --project-id my-gee-project --years 2021 2022 2023
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ee

from utils.auth import initialize_gee
from utils.export import (
    DEFAULT_YEARS,
    DRIVE_FOLDER,
    export_to_drive,
    hot_season_date_range,
    reduce_to_grid,
    wait_for_tasks,
)
from utils.geometry import get_analysis_grid, load_pune_boundary_ee

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# Sentinel-2 Constants
# ══════════════════════════════════════════════════════════════

# Sentinel-2 Level 2A — Surface Reflectance (harmonized across processors)
S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"

# QA60 bitmask positions
QA60_OPAQUE_CLOUD_BIT = 10   # Bit 10: Opaque clouds
QA60_CIRRUS_CLOUD_BIT = 11   # Bit 11: Cirrus clouds

# Maximum cloud probability (CLOUDY_PIXEL_PERCENTAGE metadata)
MAX_CLOUD_PERCENT = 30

# Sentinel-2 bands used for index computation
# B3  (Green):  560 nm, 10 m resolution
# B4  (Red):    665 nm, 10 m resolution
# B8  (NIR):    842 nm, 10 m resolution
# B11 (SWIR-1): 1610 nm, 20 m resolution


# ══════════════════════════════════════════════════════════════
# Processing Functions
# ══════════════════════════════════════════════════════════════


def mask_clouds_s2(image: ee.Image) -> ee.Image:
    """
    Mask opaque clouds and cirrus using the QA60 bitmask.

    QA60 is a per-pixel cloud mask derived from the Sentinel-2
    Level-1C cloud screening algorithm. Bits 10 and 11 indicate
    opaque and cirrus clouds respectively.
    """
    qa60 = image.select("QA60")

    cloud_mask = (
        qa60.bitwiseAnd(1 << QA60_OPAQUE_CLOUD_BIT).eq(0)
        .And(qa60.bitwiseAnd(1 << QA60_CIRRUS_CLOUD_BIT).eq(0))
    )

    return image.updateMask(cloud_mask)


def compute_spectral_indices(image: ee.Image) -> ee.Image:
    """
    Compute NDVI, NDBI, and NDWI from Sentinel-2 bands.

    Uses ee.Image.normalizedDifference() for numerically stable
    computation that handles zero-denominator cases.

    Band Formulas:
      NDVI = (B8_NIR − B4_Red)    / (B8_NIR + B4_Red)
      NDBI = (B11_SWIR − B8_NIR)  / (B11_SWIR + B8_NIR)
      NDWI = (B3_Green − B8_NIR)  / (B3_Green + B8_NIR)
    """
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
    ndbi = image.normalizedDifference(["B11", "B8"]).rename("ndbi")
    ndwi = image.normalizedDifference(["B3", "B8"]).rename("ndwi")

    return image.addBands([ndvi, ndbi, ndwi])


# ══════════════════════════════════════════════════════════════
# Main Pipeline
# ══════════════════════════════════════════════════════════════


def extract_indices_for_year(
    year: int,
    aoi: ee.Geometry,
    grid: ee.FeatureCollection,
    drive_folder: str,
) -> ee.batch.Task:
    """
    Extract median hot-season NDVI, NDBI, NDWI for a single year.

    Args:
        year:         Target year.
        aoi:          Pune boundary geometry.
        grid:         Analysis grid FeatureCollection.
        drive_folder: Google Drive folder for export.

    Returns:
        Started export task.
    """
    start_date, end_date = hot_season_date_range(year)

    logger.info(f"  Year {year}: filtering {start_date} to {end_date}")

    collection = (
        ee.ImageCollection(S2_COLLECTION)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PERCENT))
        .map(mask_clouds_s2)
        .map(compute_spectral_indices)
    )

    scene_count = collection.size()
    logger.info(f"  Year {year}: {scene_count.getInfo()} cloud-filtered scenes found")

    # Hot-season median composite for all 3 indices
    index_composite = (
        collection
        .select(["ndvi", "ndbi", "ndwi"])
        .median()
        .clip(aoi)
    )

    # Reduce to grid cells using the canonical reducer
    # For multi-band images, GEE names output properties by band name
    reduced = reduce_to_grid(index_composite, grid)

    # Export to Drive
    task = export_to_drive(
        reduced,
        description=f"spectral_indices_{year}",
        folder=drive_folder,
        selectors=["cell_code", "ndvi", "ndbi", "ndwi"],
    )

    return task


def main():
    parser = argparse.ArgumentParser(
        description="Extract Sentinel-2 NDVI, NDBI, NDWI for Pune hot seasons."
    )
    parser.add_argument(
        "--years", nargs="+", type=int, default=DEFAULT_YEARS,
        help=f"Years to process (default: {DEFAULT_YEARS})",
    )
    parser.add_argument(
        "--output-folder", default=DRIVE_FOLDER,
        help=f"Google Drive folder (default: {DRIVE_FOLDER})",
    )
    parser.add_argument(
        "--project-id", default=None,
        help="GEE Cloud project ID",
    )
    parser.add_argument(
        "--grid-asset", default=None,
        help="GEE asset ID for pre-uploaded grid (optional)",
    )
    parser.add_argument(
        "--no-wait", action="store_true",
        help="Start tasks without waiting for completion",
    )
    args = parser.parse_args()

    # Initialize GEE
    initialize_gee(args.project_id)

    # Load spatial references
    aoi = load_pune_boundary_ee()
    grid = get_analysis_grid(asset_id=args.grid_asset)

    logger.info(f"Processing spectral indices for years: {args.years}")
    logger.info(f"Export destination: Google Drive / {args.output_folder}")

    # Process each year
    tasks = []
    for year in args.years:
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing year {year}")
        logger.info(f"{'='*50}")
        task = extract_indices_for_year(year, aoi, grid, args.output_folder)
        tasks.append(task)

    # Wait for exports
    if args.no_wait:
        logger.info(
            f"Started {len(tasks)} export tasks. "
            "Check status in the GEE Code Editor Tasks tab."
        )
    else:
        wait_for_tasks(tasks)

    logger.info("\nSpectral index extraction complete!")


if __name__ == "__main__":
    main()
