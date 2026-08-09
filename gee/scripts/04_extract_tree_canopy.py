import argparse
import logging
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

import ee
from utils.auth import initialize_gee
from utils.export import (
    export_to_local_csv,
    reduce_to_grid,
)
from utils.geometry import get_analysis_grid, load_pune_boundary_ee

logger = logging.getLogger(__name__)

WORLDCOVER_V100 = "ESA/WorldCover/v100"  # 2020
WORLDCOVER_V200 = "ESA/WorldCover/v200"  # 2021
TREE_COVER_CLASS = 10

def compute_tree_fraction(aoi: ee.Geometry, version: str = "v200") -> ee.Image:
    collection_id = WORLDCOVER_V200 if version == "v200" else WORLDCOVER_V100
    worldcover = ee.ImageCollection(collection_id).first()
    
    tree_mask = (
        worldcover
        .select("Map")
        .eq(TREE_COVER_CLASS)
        .rename("tree_canopy_frac")
        .clip(aoi)
    )
    return tree_mask.toFloat()

def main():
    parser = argparse.ArgumentParser(
        description="Extract ESA WorldCover tree canopy fraction for Pune."
    )
    parser.add_argument(
        "--year", default="2021",
        help="Year of analysis",
    )
    parser.add_argument(
        "--project-id", default=None,
        help="GCP Project ID for Earth Engine initialization",
    )
    parser.add_argument(
        "--grid-asset", default=None,
        help="GEE asset ID for pre-uploaded grid (optional)",
    )
    parser.add_argument(
        "--version", default="v200", choices=["v200", "v100"],
        help="WorldCover version: v200 (2021) or v100 (2020). Default: v200",
    )
    args = parser.parse_args()

    initialize_gee(args.project_id)
    aoi = load_pune_boundary_ee()
    grid = get_analysis_grid(asset_id=args.grid_asset)

    logger.info(f"Extracting tree canopy fraction (WorldCover {args.version})")
    
    tree_mask = compute_tree_fraction(aoi, version=args.version)
    reduced = reduce_to_grid(tree_mask, grid, output_name="tree_canopy_frac")

    out_dir = str(Path(__file__).resolve().parent.parent / "exports")
    export_to_local_csv(
        feature_collection=reduced,
        description=f"canopy_{args.year}",
        out_dir=out_dir,
        selectors=["cell_code", "tree_canopy_frac"]
    )

    logger.info("Tree canopy extraction complete.")

if __name__ == "__main__":
    main()
