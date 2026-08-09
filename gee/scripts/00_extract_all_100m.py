import argparse
import logging
import time
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

import ee
from utils.auth import initialize_gee
from utils.geometry import load_pune_boundary_ee

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

# Constants
DEFAULT_YEARS = list(range(2021, 2027))
DRIVE_FOLDER = "ThermaCity_Exports"
SCALE = 100
HOT_SEASON_START_MONTH = 3
HOT_SEASON_END_MONTH = 6

LANDSAT_8_COLLECTION = "LANDSAT/LC08/C02/T1_L2"
LANDSAT_9_COLLECTION = "LANDSAT/LC09/C02/T1_L2"
S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
MAX_CLOUD_PERCENT = 20

WORLDCOVER_V100 = "ESA/WorldCover/v100"  # 2020
WORLDCOVER_V200 = "ESA/WorldCover/v200"  # 2021
TREE_COVER_CLASS = 10


def hot_season_date_range(year: int):
    return f"{year}-{HOT_SEASON_START_MONTH:02d}-01", f"{year}-{HOT_SEASON_END_MONTH:02d}-30"

# --- Landsat Processing ---
def mask_clouds_landsat(image: ee.Image) -> ee.Image:
    qa = image.select("QA_PIXEL")
    cloud_shadow_bitmask = 1 << 3
    clouds_bitmask = 1 << 5
    mask = qa.bitwiseAnd(cloud_shadow_bitmask).eq(0).And(qa.bitwiseAnd(clouds_bitmask).eq(0))
    return image.updateMask(mask)

def compute_lst_celsius(image: ee.Image) -> ee.Image:
    lst_kelvin = image.select("ST_B10").multiply(0.00341802).add(149.0)
    lst_celsius = lst_kelvin.subtract(273.15).rename("lst")
    return image.addBands(lst_celsius)

def get_lst_composite(year: int, aoi: ee.Geometry) -> ee.Image:
    start_date, end_date = hot_season_date_range(year)
    l8 = ee.ImageCollection(LANDSAT_8_COLLECTION)
    l9 = ee.ImageCollection(LANDSAT_9_COLLECTION)
    
    collection = (l8.merge(l9)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .map(mask_clouds_landsat)
        .map(compute_lst_celsius))
    return collection.select("lst").median().clip(aoi).rename("lst_observed")

# --- Sentinel Processing ---
def mask_clouds_s2(image: ee.Image) -> ee.Image:
    qa = image.select("QA60")
    cloud_bitmasks = (1 << 10) | (1 << 11)
    mask = qa.bitwiseAnd(cloud_bitmasks).eq(0)
    return image.updateMask(mask).divide(10000)

def compute_spectral_indices(image: ee.Image) -> ee.Image:
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
    ndbi = image.normalizedDifference(["B11", "B8"]).rename("ndbi")
    ndwi = image.normalizedDifference(["B3", "B8"]).rename("ndwi")
    return image.addBands([ndvi, ndbi, ndwi])

def get_indices_composite(year: int, aoi: ee.Geometry) -> ee.Image:
    start_date, end_date = hot_season_date_range(year)
    collection = (ee.ImageCollection(S2_COLLECTION)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PERCENT))
        .map(mask_clouds_s2)
        .map(compute_spectral_indices))
    return collection.select(["ndvi", "ndbi", "ndwi"]).median().clip(aoi)

# --- WorldCover Processing ---
def get_tree_canopy(aoi: ee.Geometry) -> ee.Image:
    worldcover = ee.ImageCollection(WORLDCOVER_V200).first()
    tree_mask = worldcover.select("Map").eq(TREE_COVER_CLASS).rename("tree_canopy_frac").clip(aoi)
    return tree_mask.toFloat()

# --- Main Logic ---
def main():
    parser = argparse.ArgumentParser(description="Monolithic 100m Server-Side GEE Extraction for ThermaCity")
    parser.add_argument("--years", type=int, nargs="+", default=DEFAULT_YEARS)
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--no-wait", action="store_true")
    args = parser.parse_args()

    initialize_gee(args.project_id)
    aoi = load_pune_boundary_ee()

    logger.info("Extracting Tree Canopy Base Layer...")
    tree_canopy = get_tree_canopy(aoi)

    tasks = []
    
    for year in args.years:
        logger.info(f"\n{'='*50}\nProcessing year {year}\n{'='*50}")
        
        lst = get_lst_composite(year, aoi)
        indices = get_indices_composite(year, aoi)
        
        # 1. Combine layers
        combined = ee.Image.cat([lst, indices, tree_canopy])
        
        # 2. Server-side Sampling
        logger.info(f"  Sampling combined layers at {SCALE}m scale...")
        sampled_grid = combined.sample(
            region=aoi,
            scale=SCALE,
            geometries=True
        )
        
        # 3. Download CSV Synchronously
        out_dir = Path(__file__).resolve().parent.parent / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        task_name = f"ThermaCity_Pune_100m_{year}"
        out_file = out_dir / f"{task_name}.csv"

        logger.info(f"  Downloading {task_name}.csv synchronously...")
        try:
            url = sampled_grid.getDownloadURL(
                filetype="CSV",
                filename=task_name
            )
            import urllib.request
            urllib.request.urlretrieve(url, str(out_file))
            logger.info(f"  [✓] Downloaded to {out_file}")
        except Exception as e:
            logger.error(f"  [X] Failed to download {task_name}: {e}")
            
    logger.info("All 100m extractions downloaded successfully!")

if __name__ == "__main__":
    main()
