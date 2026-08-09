"""
ThermaCity — Google Earth Engine Automated Extraction Worker

Extracts the latest satellite data for Pune at 100m resolution:
  - Landsat 8/9 Land Surface Temperature (LST)
  - Sentinel-2 NDVI, NDBI, NDWI
  - ESA WorldCover Tree Canopy Fraction

Usage:
    cd backend
    python scripts/gee_worker.py --year 2025
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import ee
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

# Pune bounding box (EPSG:4326)
PUNE_BBOX = [73.75, 18.40, 73.95, 18.62]


def authenticate_gee():
    """Authenticate with GEE using service account."""
    key_path = Path(__file__).resolve().parent.parent.parent / "credentials" / "thermacity-504715-08378215d2cd.json"
    if not key_path.exists():
        logger.error("GEE service account key not found at %s", key_path)
        sys.exit(1)

    credentials = ee.ServiceAccountCredentials(
        'thermacity-backend@thermacity-504715.iam.gserviceaccount.com',
        str(key_path)
    )
    ee.Initialize(credentials)
    logger.info("GEE authenticated successfully.")


def get_pune_aoi():
    """Create Earth Engine geometry for Pune."""
    return ee.Geometry.Rectangle(PUNE_BBOX)


def extract_data(year: int) -> pd.DataFrame:
    """Extract unified satellite data for a given year."""
    aoi = get_pune_aoi()
    start_date = f"{year}-03-01"  # Hot season: March-June
    end_date = f"{year}-06-30"

    logger.info("Extracting data for year %d (Mar-Jun)...", year)

    # ── 1. Landsat 8/9 LST ────────────────────────────────────
    landsat = (
        ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        .merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2'))
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt('CLOUD_COVER', 20))
    )

    def compute_lst(image):
        thermal = image.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15)
        return thermal.rename('lst_observed').copyProperties(image, ['system:time_start'])

    lst_median = landsat.map(compute_lst).median().clip(aoi)

    # ── 2. Sentinel-2 Indices ─────────────────────────────────
    s2 = (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    )

    def compute_indices(image):
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndbi = image.normalizedDifference(['B11', 'B8']).rename('ndbi')
        ndwi = image.normalizedDifference(['B3', 'B8']).rename('ndwi')
        return ndvi.addBands(ndbi).addBands(ndwi).copyProperties(image, ['system:time_start'])

    indices_median = s2.map(compute_indices).median().clip(aoi)

    # ── 3. ESA WorldCover Tree Canopy ─────────────────────────
    worldcover = ee.ImageCollection('ESA/WorldCover/v200').first().clip(aoi)
    # Tree cover (class 10) fraction in 100m cells
    tree_mask = worldcover.eq(10).rename('tree_canopy_frac')

    # ── 4. Stack all layers ───────────────────────────────────
    stacked = ee.Image.cat([
        lst_median,
        indices_median,
        tree_mask.reduceResolution(
            reducer=ee.Reducer.mean(),
            maxPixels=1024
        ).reproject(crs='EPSG:4326', scale=100)
    ])

    # ── 5. Sample at 100m resolution ──────────────────────────
    logger.info("Sampling at 100m resolution...")
    samples = stacked.sample(
        region=aoi,
        scale=100,
        geometries=True,
        seed=42
    )

    # ── 6. Download results ───────────────────────────────────
    logger.info("Downloading sampled data...")
    features = samples.getInfo()['features']
    logger.info("Downloaded %d features.", len(features))

    rows = []
    for f in features:
        props = f['properties']
        geom = f['geometry']
        props['.geo'] = json.dumps(geom)
        props['year'] = year
        rows.append(props)

    df = pd.DataFrame(rows)
    return df


def main():
    parser = argparse.ArgumentParser(description='ThermaCity GEE Data Extraction Worker')
    parser.add_argument('--year', type=int, default=datetime.now().year, help='Year to extract data for')
    parser.add_argument('--output', type=str, default=None, help='Output CSV path')
    args = parser.parse_args()

    authenticate_gee()

    t0 = time.time()
    df = extract_data(args.year)

    # Save output
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path(__file__).resolve().parent.parent.parent / 'ml' / 'data'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'gee_extract_{args.year}.csv'

    df.to_csv(output_path, index=False)
    elapsed = time.time() - t0

    logger.info("=" * 60)
    logger.info("Extraction complete in %.1f seconds", elapsed)
    logger.info("  Year: %d", args.year)
    logger.info("  Rows: %d", len(df))
    logger.info("  Output: %s", output_path)
    logger.info("  Columns: %s", list(df.columns))
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
