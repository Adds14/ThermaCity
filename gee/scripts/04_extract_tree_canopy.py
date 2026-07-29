#!/usr/bin/env python3
"""
ThermaCity — 04: ESA WorldCover Tree Canopy Fraction Extraction

Extracts tree canopy cover fraction from the ESA WorldCover 10 m
land cover map. The WorldCover product classifies each 10 m pixel
into one of 11 land cover classes. We reclassify into a binary
tree/non-tree mask and reduce with mean() to compute the fraction
of tree cover within each 100×100 m grid cell.

Processing Chain:
  1. Load ESA WorldCover (v200 for 2021, v100 for 2020)
  2. Reclassify: Tree Cover (class 10) → 1, all others → 0
  3. Reduce binary mask to grid via ee.Reducer.mean()
     (mean of a binary raster = fraction of class-1 pixels)
  4. Export to Google Drive as CSV

ESA WorldCover Classes:
  10 = Tree Cover           ← WE USE THIS
  20 = Shrubland
  30 = Grassland
  40 = Cropland
  50 = Built-up
  60 = Bare / sparse vegetation
  70 = Snow and ice
  80 = Permanent water bodies
  90 = Herbaceous wetland
  95 = Mangroves
  100 = Moss and lichen

Temporal Note:
  WorldCover v200 covers 2021 only. For the 2021–2026 analysis window,
  we apply the 2021 tree canopy fraction to ALL years. This is a
  reasonable assumption for the MVP since urban tree canopy changes
  slowly (typically < 5% per year). Future versions can incorporate
  annual canopy change detection.

Output Columns:
  - cell_code:        Grid cell identifier
  - tree_canopy_frac: Fraction of cell covered by trees (0.0–1.0)

Usage:
    python 04_extract_tree_canopy.py --project-id my-gee-project
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ee

from utils.auth import initialize_gee
from utils.export import (
    DRIVE_FOLDER,
    export_to_drive,
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
# ESA WorldCover Constants
# ══════════════════════════════════════════════════════════════

# WorldCover v200 (2021) — 10 m resolution global land cover
WORLDCOVER_V200 = "ESA/WorldCover/v200"    # 2021 epoch
WORLDCOVER_V100 = "ESA/WorldCover/v100"    # 2020 epoch (fallback)

# Land cover class for tree cover
TREE_COVER_CLASS = 10


# ══════════════════════════════════════════════════════════════
# Processing Functions
# ══════════════════════════════════════════════════════════════


def compute_tree_fraction(
    aoi: ee.Geometry,
    version: str = "v200",
) -> ee.Image:
    """
    Create a binary tree cover mask from ESA WorldCover.

    The WorldCover 'Map' band has integer values 10–100 representing
    land cover classes. We reclassify tree cover (class 10) as 1 and
    everything else as 0.

    When this binary image is reduced with ee.Reducer.mean(), the result
    is the fraction of 10 m pixels that are tree-covered — which is
    exactly the tree canopy fraction per grid cell.

    Args:
        aoi:     Pune boundary geometry.
        version: WorldCover version ('v200' for 2021, 'v100' for 2020).

    Returns:
        ee.Image with a single band 'tree_canopy_frac' (values 0 or 1).
    """
    if version == "v200":
        collection_id = WORLDCOVER_V200
    elif version == "v100":
        collection_id = WORLDCOVER_V100
    else:
        raise ValueError(f"Unknown WorldCover version: {version}")

    logger.info(f"Loading WorldCover {version} ({collection_id})")

    # WorldCover is a single-image collection — take the first (and only) image
    worldcover = ee.ImageCollection(collection_id).first()

    # Reclassify: tree cover (10) → 1, all other classes → 0
    tree_mask = (
        worldcover
        .select("Map")
        .eq(TREE_COVER_CLASS)
        .rename("tree_canopy_frac")
        .clip(aoi)
    )

    # Explicitly cast to float so mean() returns fractional values
    tree_mask = tree_mask.toFloat()

    return tree_mask


# ══════════════════════════════════════════════════════════════
# Main Pipeline
# ══════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Extract ESA WorldCover tree canopy fraction for Pune."
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
        "--version", default="v200", choices=["v200", "v100"],
        help="WorldCover version: v200 (2021) or v100 (2020). Default: v200",
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

    logger.info(f"Extracting tree canopy fraction (WorldCover {args.version})")
    logger.info(f"Export destination: Google Drive / {args.output_folder}")

    # Compute binary tree mask
    tree_mask = compute_tree_fraction(aoi, version=args.version)

    # Reduce to grid — mean of binary mask = fraction of tree-covered pixels
    # Since the tree mask is at 10 m and our grid is 100 m,
    # each cell contains ~100 WorldCover pixels (10×10).
    # The mean gives a smooth fraction (0.0 to 1.0).
    logger.info("Reducing tree mask to grid (10 m → 100 m aggregation)...")
    reduced = reduce_to_grid(tree_mask, grid, output_name="tree_canopy_frac")

    # Export — single file, not per-year (static land cover)
    year_tag = "2021" if args.version == "v200" else "2020"
    task = export_to_drive(
        reduced,
        description=f"tree_canopy_{year_tag}",
        folder=args.output_folder,
        selectors=["cell_code", "tree_canopy_frac"],
    )

    if args.no_wait:
        logger.info(
            "Export task started. Check status in the GEE Code Editor Tasks tab."
        )
    else:
        wait_for_tasks([task])

    logger.info("\nTree canopy fraction extraction complete!")
    logger.info(
        "NOTE: This single export is applied to all analysis years (2021–2026) "
        "in the merge step, as urban tree canopy changes slowly."
    )


if __name__ == "__main__":
    main()
