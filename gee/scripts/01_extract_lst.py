#!/usr/bin/env python3
"""
ThermaCity — 01: Landsat 8/9 Land Surface Temperature Extraction

Extracts LST from Landsat Collection 2 Level 2 Science Products.
The ST_B10 band provides pre-computed Surface Temperature which
we scale to Celsius and composite into a hot-season median.

Processing Chain:
  1. Merge Landsat 8 (LC08) and Landsat 9 (LC09) collections
  2. Filter to Pune AOI and hot season (March–June)
  3. Mask clouds and cloud shadows using QA_PIXEL bitmask
  4. Scale ST_B10 to Kelvin (DN × 0.00341802 + 149.0) → Celsius (−273.15)
  5. Compute median composite per hot season
  6. Reduce to 100×100 m grid via ee.Reducer.mean()
  7. Export to Google Drive as CSV

Output Columns:
  - cell_code: Grid cell identifier (e.g., "PUNE_R0042_C0117")
  - lst:       Median hot-season Land Surface Temperature (°C)

Usage:
    python 01_extract_lst.py --project-id my-gee-project --years 2021 2022 2023 2024 2025 2026
"""

import argparse
import logging
import sys
from pathlib import Path

# Add the gee/ root to sys.path so `utils` is importable
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
# Landsat Constants
# ══════════════════════════════════════════════════════════════

# Landsat Collection 2 Level 2 — Surface Temperature product
LANDSAT_8_COLLECTION = "LANDSAT/LC08/C02/T1_L2"
LANDSAT_9_COLLECTION = "LANDSAT/LC09/C02/T1_L2"

# ST_B10 scaling factors (Collection 2 Level 2 Science Products)
# DN → Kelvin: (DN × SCALE_FACTOR) + OFFSET
ST_SCALE_FACTOR = 0.00341802
ST_OFFSET = 149.0
KELVIN_TO_CELSIUS = 273.15

# QA_PIXEL bitmask positions (Landsat Collection 2)
QA_CLOUD_BIT = 3          # Bit 3: Cloud
QA_CLOUD_SHADOW_BIT = 4   # Bit 4: Cloud Shadow
QA_SNOW_BIT = 5            # Bit 5: Snow (exclude for thermal accuracy)


# ══════════════════════════════════════════════════════════════
# Processing Functions
# ══════════════════════════════════════════════════════════════


def mask_clouds_landsat(image: ee.Image) -> ee.Image:
    """
    Mask cloud, cloud shadow, and snow pixels using QA_PIXEL.

    The QA_PIXEL band in Landsat Collection 2 Level 2 uses a bitmask
    where set bits indicate the presence of atmospheric artifacts.
    We mask all three for cleaner thermal composites.
    """
    qa = image.select("QA_PIXEL")

    # Create mask: 0 where cloud/shadow/snow bits are set
    cloud_mask = (
        qa.bitwiseAnd(1 << QA_CLOUD_BIT).eq(0)
        .And(qa.bitwiseAnd(1 << QA_CLOUD_SHADOW_BIT).eq(0))
        .And(qa.bitwiseAnd(1 << QA_SNOW_BIT).eq(0))
    )

    return image.updateMask(cloud_mask)


def compute_lst_celsius(image: ee.Image) -> ee.Image:
    """
    Convert ST_B10 from scaled DN to Land Surface Temperature in °C.

    Landsat Collection 2 Level 2 provides pre-computed surface temperature
    in the ST_B10 band. The DN values need scaling:
      Kelvin = DN × 0.00341802 + 149.0
      Celsius = Kelvin − 273.15

    Also applies a validity filter: LST must be between -10°C and 70°C
    to exclude sensor artifacts and fill values.
    """
    lst_kelvin = (
        image.select("ST_B10")
        .multiply(ST_SCALE_FACTOR)
        .add(ST_OFFSET)
    )

    lst_celsius = lst_kelvin.subtract(KELVIN_TO_CELSIUS).rename("lst")

    # Mask unrealistic values (fill pixels, sensor errors)
    valid_mask = lst_celsius.gt(-10).And(lst_celsius.lt(70))
    lst_celsius = lst_celsius.updateMask(valid_mask)

    return image.addBands(lst_celsius)


# ══════════════════════════════════════════════════════════════
# Main Pipeline
# ══════════════════════════════════════════════════════════════


def extract_lst_for_year(
    year: int,
    aoi: ee.Geometry,
    grid: ee.FeatureCollection,
    drive_folder: str,
) -> ee.batch.Task:
    """
    Extract median hot-season LST for a single year.

    Args:
        year:         Target year (e.g., 2023).
        aoi:          Pune boundary geometry.
        grid:         Analysis grid FeatureCollection.
        drive_folder: Google Drive folder for export.

    Returns:
        Started export task.
    """
    start_date, end_date = hot_season_date_range(year)

    logger.info(f"  Year {year}: filtering {start_date} to {end_date}")

    # Merge Landsat 8 and 9 collections
    l8 = ee.ImageCollection(LANDSAT_8_COLLECTION)
    l9 = ee.ImageCollection(LANDSAT_9_COLLECTION)

    collection = (
        l8.merge(l9)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .map(mask_clouds_landsat)
        .map(compute_lst_celsius)
    )

    # Log scene count (for diagnostics)
    scene_count = collection.size()
    logger.info(f"  Year {year}: {scene_count.getInfo()} cloud-free scenes found")

    # Hot-season median composite (single band: 'lst')
    lst_composite = collection.select("lst").median().clip(aoi)

    # Reduce to grid cells using the canonical reducer
    reduced = reduce_to_grid(lst_composite, grid, output_name="lst")

    # Export to Drive (only cell_code and lst columns)
    task = export_to_drive(
        reduced,
        description=f"lst_{year}",
        folder=drive_folder,
        selectors=["cell_code", "lst"],
    )

    return task


def main():
    parser = argparse.ArgumentParser(
        description="Extract Landsat 8/9 LST for Pune hot seasons."
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

    logger.info(f"Processing LST for years: {args.years}")
    logger.info(f"Export destination: Google Drive / {args.output_folder}")

    # Process each year
    tasks = []
    for year in args.years:
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing year {year}")
        logger.info(f"{'='*50}")
        task = extract_lst_for_year(year, aoi, grid, args.output_folder)
        tasks.append(task)

    # Wait for exports
    if args.no_wait:
        logger.info(
            f"Started {len(tasks)} export tasks. "
            "Check status in the GEE Code Editor Tasks tab."
        )
    else:
        wait_for_tasks(tasks)

    logger.info("\nLST extraction complete!")


if __name__ == "__main__":
    main()
