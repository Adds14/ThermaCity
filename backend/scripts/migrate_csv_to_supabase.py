"""
ThermaCity — Migrate training_set.csv → Supabase PostGIS

This script:
  1. Connects to Supabase PostgreSQL (sync via psycopg2)
  2. Runs the init_postgis.sql to create tables (idempotent)
  3. Reads training_set.csv
  4. For each unique cell (based on .geo coordinate), creates a spatial_grid row
  5. For each row, inserts environmental_features with ML predictions and HVI scores
  6. Commits in batches for performance

Usage:
    cd backend
    python scripts/migrate_csv_to_supabase.py
"""

import json
import sys
import time
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# Add parent to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.ml_predictor import MLPredictor
from app.services.hvi_calculator import HVICalculator

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)


def get_sync_url() -> str:
    """Convert the asyncpg URL to a psycopg2-compatible URL."""
    url = settings.database_url.replace("+asyncpg", "")
    return url


def point_to_wkt(geo_str: str) -> tuple[str, float, float] | None:
    """Convert a GEE .geo JSON string to a WKT polygon + centroid."""
    try:
        geom = json.loads(geo_str)
        if geom.get("type") != "Point":
            return None
        lon, lat = geom["coordinates"]
        d = 0.00045  # ~50m offset → 100m square
        wkt = (
            f"SRID=4326;POLYGON(("
            f"{lon-d} {lat-d},"
            f"{lon+d} {lat-d},"
            f"{lon+d} {lat+d},"
            f"{lon-d} {lat+d},"
            f"{lon-d} {lat-d}))"
        )
        return wkt, lat, lon
    except Exception:
        return None


def main():
    t0 = time.time()

    # ── 1. Find CSV ──────────────────────────────────────────
    csv_path = Path(__file__).resolve().parent.parent.parent / "ml" / "data" / "training_set.csv"
    if not csv_path.exists():
        logger.error("CSV not found at %s", csv_path)
        sys.exit(1)

    logger.info("Reading CSV: %s", csv_path)
    df = pd.read_csv(csv_path)
    logger.info("CSV loaded: %d rows, columns: %s", len(df), list(df.columns))

    # ── 2. Load ML model for predictions ─────────────────────
    model_path = Path(__file__).resolve().parent.parent.parent / "ml" / "models" / "rf_lst_predictor_v1.joblib"
    predictor = MLPredictor(model_path)

    # ── 3. Run ML predictions ────────────────────────────────
    logger.info("Running ML predictions on %d rows...", len(df))
    features_list = df[["ndvi", "ndbi", "ndwi", "tree_canopy_frac"]].to_dict("records")
    lst_predictions = predictor.predict_batch(features_list)
    df["lst_predicted"] = lst_predictions

    # ── 4. Compute HVI per year (batch normalisation) ────────
    logger.info("Computing HVI scores per year...")
    df["hvi_score"] = np.nan
    df["hvi_tier"] = ""

    for year in df["year"].unique():
        mask = df["year"] == year
        year_df = df.loc[mask]

        hvi_rows = []
        for _, row in year_df.iterrows():
            hvi_rows.append({
                "lst_predicted": row["lst_predicted"],
                "humidity": 55.0,
                "wind_speed": 2.0,
                "population_density": 10000.0,
                "tree_canopy_frac": row.get("tree_canopy_frac", 0.0),
            })

        hvi_results = HVICalculator.compute_batch(hvi_rows)
        df.loc[mask, "hvi_score"] = [r["hvi_score"] for r in hvi_results]
        df.loc[mask, "hvi_tier"] = [r["hvi_tier"] for r in hvi_results]

    logger.info("HVI computed for all years.")

    # ── 5. Parse geometries ──────────────────────────────────
    logger.info("Parsing geometries...")
    geo_data = df[".geo"].apply(point_to_wkt)
    valid_mask = geo_data.notnull()
    logger.info("Valid geometries: %d / %d", valid_mask.sum(), len(df))

    df = df[valid_mask].copy()
    df["wkt"] = geo_data[valid_mask].apply(lambda x: x[0])
    df["centroid_lat"] = geo_data[valid_mask].apply(lambda x: x[1])
    df["centroid_lng"] = geo_data[valid_mask].apply(lambda x: x[2])

    # Create unique cell identifier from coordinates
    df["cell_code"] = df.apply(
        lambda r: f"PUNE_{r['centroid_lat']:.4f}_{r['centroid_lng']:.4f}", axis=1
    )

    # ── 6. Connect to Supabase ───────────────────────────────
    db_url = get_sync_url()
    logger.info("Connecting to Supabase...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    # ── 7. Run init SQL ──────────────────────────────────────
    init_sql_path = Path(__file__).resolve().parent / "init_postgis.sql"
    if init_sql_path.exists():
        logger.info("Running init_postgis.sql...")
        sql = init_sql_path.read_text()
        # Split and execute statement by statement to handle IF NOT EXISTS gracefully
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt and not stmt.startswith("--"):
                try:
                    cur.execute(stmt)
                except psycopg2.errors.DuplicateObject as e:
                    conn.rollback()
                    logger.warning("Already exists (skipping): %s", str(e).split("\n")[0])
                except Exception as e:
                    conn.rollback()
                    logger.warning("SQL warning: %s", str(e).split("\n")[0])
        conn.commit()
        logger.info("Schema initialised.")
    else:
        logger.warning("init_postgis.sql not found, assuming tables exist.")

    # ── 8. Insert spatial_grid (unique cells) ────────────────
    logger.info("Inserting spatial grid cells...")

    # Get unique cells
    unique_cells = df.drop_duplicates(subset=["cell_code"])[
        ["cell_code", "centroid_lat", "centroid_lng", "wkt"]
    ].copy()

    # Clear existing data (full refresh)
    cur.execute("DELETE FROM environmental_features")
    cur.execute("DELETE FROM spatial_grid")
    conn.commit()
    logger.info("Cleared existing data.")

    # Batch insert grid cells
    grid_values = []
    for _, row in unique_cells.iterrows():
        grid_values.append((
            row["cell_code"],
            row["centroid_lat"],
            row["centroid_lng"],
            row["wkt"],
        ))

    BATCH = 2000
    for i in range(0, len(grid_values), BATCH):
        batch = grid_values[i:i + BATCH]
        execute_values(
            cur,
            """
            INSERT INTO spatial_grid (cell_code, centroid_lat, centroid_lng, geom)
            VALUES %s
            ON CONFLICT (cell_code) DO NOTHING
            """,
            batch,
            template="(%s, %s, %s, ST_GeomFromEWKT(%s))",
        )
        conn.commit()
        logger.info("  Grid cells: %d / %d", min(i + BATCH, len(grid_values)), len(grid_values))

    # ── 9. Build cell_code → id mapping ──────────────────────
    cur.execute("SELECT id, cell_code FROM spatial_grid")
    code_to_id = {code: gid for gid, code in cur.fetchall()}
    logger.info("Grid cell mapping: %d entries", len(code_to_id))

    # ── 10. Insert environmental_features ────────────────────
    logger.info("Inserting environmental features...")

    feat_values = []
    skipped = 0
    for _, row in df.iterrows():
        grid_id = code_to_id.get(row["cell_code"])
        if grid_id is None:
            skipped += 1
            continue

        feat_values.append((
            grid_id,
            int(row["year"]),
            float(row["lst_observed"]) if pd.notna(row["lst_observed"]) else None,
            float(row["ndvi"]) if pd.notna(row["ndvi"]) else None,
            float(row["ndbi"]) if pd.notna(row["ndbi"]) else None,
            float(row["ndwi"]) if pd.notna(row["ndwi"]) else None,
            float(row["tree_canopy_frac"]) if pd.notna(row["tree_canopy_frac"]) else None,
            55.0,   # humidity default
            2.0,    # wind_speed default
            10000.0,  # population_density default
            float(row["lst_predicted"]),
            float(row["hvi_score"]),
            row["hvi_tier"],
        ))

    for i in range(0, len(feat_values), BATCH):
        batch = feat_values[i:i + BATCH]
        execute_values(
            cur,
            """
            INSERT INTO environmental_features
                (grid_id, year, lst_observed, ndvi, ndbi, ndwi, tree_canopy_frac,
                 humidity, wind_speed, population_density, lst_predicted, hvi_score, hvi_tier)
            VALUES %s
            ON CONFLICT (grid_id, year) DO UPDATE SET
                lst_observed = EXCLUDED.lst_observed,
                ndvi = EXCLUDED.ndvi,
                ndbi = EXCLUDED.ndbi,
                ndwi = EXCLUDED.ndwi,
                tree_canopy_frac = EXCLUDED.tree_canopy_frac,
                lst_predicted = EXCLUDED.lst_predicted,
                hvi_score = EXCLUDED.hvi_score,
                hvi_tier = EXCLUDED.hvi_tier,
                updated_at = now()
            """,
            batch,
        )
        conn.commit()
        logger.info("  Features: %d / %d", min(i + BATCH, len(feat_values)), len(feat_values))

    if skipped:
        logger.warning("Skipped %d rows (no matching grid cell)", skipped)

    # ── 11. Verify ───────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM spatial_grid")
    grid_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM environmental_features")
    feat_count = cur.fetchone()[0]

    cur.execute("SELECT year, COUNT(*) FROM environmental_features GROUP BY year ORDER BY year")
    year_counts = cur.fetchall()

    cur.close()
    conn.close()

    elapsed = time.time() - t0
    logger.info("=" * 60)
    logger.info("Migration complete in %.1f seconds", elapsed)
    logger.info("  spatial_grid rows: %d", grid_count)
    logger.info("  environmental_features rows: %d", feat_count)
    for year, count in year_counts:
        logger.info("    Year %d: %d cells", year, count)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
