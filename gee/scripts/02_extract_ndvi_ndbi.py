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

S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
MAX_CLOUD_PERCENT = 20

def mask_clouds_s2(image: ee.Image) -> ee.Image:
    qa = image.select("QA60")
    cloud_bitmasks = (1 << 10) | (1 << 11)
    mask = qa.bitwiseAnd(cloud_bitmasks).eq(0)
    return image.updateMask(mask).divide(10000)

def compute_spectral_indices(image: ee.Image) -> ee.Image:
    nir = image.select("B8")
    red = image.select("B4")
    swir = image.select("B11")
    green = image.select("B3")

    ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
    ndbi = image.normalizedDifference(["B11", "B8"]).rename("ndbi")
    ndwi = image.normalizedDifference(["B3", "B8"]).rename("ndwi")

    return image.addBands([ndvi, ndbi, ndwi])

def extract_indices_for_year(
    year: int, aoi: ee.Geometry, grid: ee.FeatureCollection
) -> ee.FeatureCollection:
    start_date, end_date = hot_season_date_range(year)
    
    collection = (
        ee.ImageCollection(S2_COLLECTION)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PERCENT))
        .map(mask_clouds_s2)
        .map(compute_spectral_indices)
    )

    index_composite = collection.select(["ndvi", "ndbi", "ndwi"]).median().clip(aoi)
    reduced = reduce_to_grid(index_composite, grid)
    return reduced

def main():
    parser = argparse.ArgumentParser(
        description="Extract Sentinel-2 NDVI, NDBI, NDWI for Pune hot seasons."
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

    logger.info(f"Processing indices for years: {args.years}")
    out_dir = str(Path(__file__).resolve().parent.parent / "exports")

    for year in args.years:
        logger.info(f"\n{'='*50}\nProcessing year {year}\n{'='*50}")
        reduced = extract_indices_for_year(year, aoi, grid)
        
        logger.info(f"Exporting year {year} to {out_dir}")
        export_to_local_csv(
            feature_collection=reduced,
            description=f"spectral_indices_{year}",
            out_dir=out_dir,
            selectors=["cell_code", "ndvi", "ndbi", "ndwi"]
        )

    logger.info("Indices extraction complete.")

if __name__ == "__main__":
    main()
