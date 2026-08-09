import argparse
import logging
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

import ee
from utils.auth import initialize_gee
from utils.export import (
    DEFAULT_YEARS,
    export_to_local_csv,
    hot_season_date_range,
    reduce_to_grid,
)
from utils.geometry import get_analysis_grid, load_pune_boundary_ee

logger = logging.getLogger(__name__)

LANDSAT_8_COLLECTION = "LANDSAT/LC08/C02/T1_L2"
LANDSAT_9_COLLECTION = "LANDSAT/LC09/C02/T1_L2"

def mask_clouds_landsat(image: ee.Image) -> ee.Image:
    qa = image.select("QA_PIXEL")
    cloud_shadow_bitmask = 1 << 3
    clouds_bitmask = 1 << 5
    mask = (
        qa.bitwiseAnd(cloud_shadow_bitmask)
        .eq(0)
        .And(qa.bitwiseAnd(clouds_bitmask).eq(0))
    )
    return image.updateMask(mask)

def compute_lst_celsius(image: ee.Image) -> ee.Image:
    lst_kelvin = image.select("ST_B10").multiply(0.00341802).add(149.0)
    lst_celsius = lst_kelvin.subtract(273.15).rename("lst")
    return image.addBands(lst_celsius)

def extract_lst_for_year(
    year: int, aoi: ee.Geometry, grid: ee.FeatureCollection
) -> ee.FeatureCollection:
    start_date, end_date = hot_season_date_range(year)
    logger.info(f"  Year {year}: filtering {start_date} to {end_date}")

    l8 = ee.ImageCollection(LANDSAT_8_COLLECTION)
    l9 = ee.ImageCollection(LANDSAT_9_COLLECTION)

    collection = (
        l8.merge(l9)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .map(mask_clouds_landsat)
        .map(compute_lst_celsius)
    )

    scene_count = collection.size()
    logger.info(f"  Year {year}: {scene_count.getInfo()} cloud-free scenes found")

    lst_composite = collection.select("lst").median().clip(aoi)
    reduced = reduce_to_grid(lst_composite, grid, output_name="lst_observed")

    return reduced

def main():
    parser = argparse.ArgumentParser(
        description="Extract Landsat 8/9 LST for Pune hot seasons."
    )
    parser.add_argument(
        "--years", type=int, nargs="+", default=DEFAULT_YEARS,
        help="Years to process (e.g., 2021 2022)",
    )
    parser.add_argument(
        "--project-id", default=None,
        help="GCP Project ID for Earth Engine initialization",
    )
    parser.add_argument(
        "--grid-asset", default=None,
        help="GEE asset ID for pre-uploaded grid (optional)",
    )
    args = parser.parse_args()

    initialize_gee(args.project_id)

    aoi = load_pune_boundary_ee()
    grid = get_analysis_grid(asset_id=args.grid_asset)

    logger.info(f"Processing LST for years: {args.years}")

    out_dir = str(Path(__file__).resolve().parent.parent / "exports")
    
    for year in args.years:
        logger.info(f"\n{'='*50}\nProcessing year {year}\n{'='*50}")
        reduced = extract_lst_for_year(year, aoi, grid)
        
        logger.info(f"Exporting year {year} to {out_dir}")
        export_to_local_csv(
            feature_collection=reduced,
            description=f"lst_{year}",
            out_dir=out_dir,
            selectors=["cell_code", "lst_observed"]
        )

    logger.info("LST extraction complete.")

if __name__ == "__main__":
    main()
