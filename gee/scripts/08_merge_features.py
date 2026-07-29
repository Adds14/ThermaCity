#!/usr/bin/env python3
"""
ThermaCity — 08: Feature Matrix Merge Utility

Joins all GEE-exported CSVs by `cell_code` and `year` to produce
the unified training set for the Random Forest model.

Expected Input CSVs (downloaded from Google Drive):
  - lst_{year}.csv              → columns: cell_code, lst
  - spectral_indices_{year}.csv → columns: cell_code, ndvi, ndbi, ndwi
  - tree_canopy_2021.csv        → columns: cell_code, tree_canopy_frac
  - era5_{year}.csv             → columns: cell_code, humidity, wind_speed     (Phase 2)
  - population_{year}.csv       → columns: cell_code, population_density       (Phase 2)

Merge Strategy:
  1. For each year, join LST and spectral indices CSVs on `cell_code`.
  2. Left-join the static tree canopy layer (applied to all years).
  3. Left-join ERA5 climate and WorldPop population data (when available).
  4. Add a `year` column.
  5. Concatenate all years into a single DataFrame.
  6. Validate: check for null rates, value ranges, join completeness.
  7. Export as `training_set.csv`.

Quality Checks:
  - Warns if any layer has > 10% null values (possible cloud contamination)
  - Warns if LST values fall outside 20–55°C range (Pune hot season)
  - Warns if NDVI/NDBI/NDWI values fall outside [-1, 1]
  - Reports per-year cell counts and overall merge statistics

Usage:
    python 08_merge_features.py --input-dir ./exports --output ../ml/data/training_set.csv
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# File Discovery
# ══════════════════════════════════════════════════════════════

# Expected filename patterns (case-insensitive matching)
FILE_PATTERNS = {
    "lst":              "lst_{year}.csv",
    "spectral_indices": "spectral_indices_{year}.csv",
    "tree_canopy":      "tree_canopy_*.csv",       # Static — no year suffix
    "era5":             "era5_{year}.csv",          # Phase 2
    "population":       "population_{year}.csv",    # Phase 2
}

DEFAULT_YEARS = list(range(2021, 2027))

# Column renaming for single-band exports that use 'mean' as column name
COLUMN_RENAMES = {
    "mean": None,  # Will be handled per-file based on context
}


def find_csv(input_dir: Path, pattern: str) -> Path | None:
    """Find a CSV file matching the given pattern in input_dir."""
    matches = list(input_dir.glob(pattern))
    if not matches:
        return None
    if len(matches) > 1:
        logger.warning(
            f"  Multiple files match '{pattern}': {[m.name for m in matches]}. "
            f"Using: {matches[0].name}"
        )
    return matches[0]


def load_csv(path: Path, expected_columns: list[str] | None = None) -> pd.DataFrame:
    """
    Load a GEE-exported CSV with validation.

    GEE CSVs may include extra columns like 'system:index' and '.geo'.
    We drop those and validate expected columns exist.
    """
    df = pd.read_csv(path)

    # Drop GEE system columns
    gee_system_cols = [
        col for col in df.columns
        if col.startswith("system:") or col == ".geo"
    ]
    if gee_system_cols:
        df = df.drop(columns=gee_system_cols)

    # Drop 'mean' if a named column already exists (multi-band exports)
    if "mean" in df.columns and len(df.columns) > 2:
        df = df.drop(columns=["mean"], errors="ignore")

    if expected_columns:
        missing = set(expected_columns) - set(df.columns)
        if missing:
            logger.warning(
                f"  Missing expected columns in {path.name}: {missing}. "
                f"Available: {list(df.columns)}"
            )

    logger.info(f"  Loaded {path.name}: {len(df)} rows, columns={list(df.columns)}")
    return df


# ══════════════════════════════════════════════════════════════
# Merge Logic
# ══════════════════════════════════════════════════════════════


def merge_year(
    year: int,
    input_dir: Path,
    tree_canopy_df: pd.DataFrame | None,
) -> pd.DataFrame | None:
    """
    Merge all feature CSVs for a single year.

    Args:
        year:            Target year.
        input_dir:       Directory containing GEE CSV exports.
        tree_canopy_df:  Static tree canopy DataFrame (applied to all years).

    Returns:
        Merged DataFrame with columns:
        [cell_code, year, lst, ndvi, ndbi, ndwi, tree_canopy_frac,
         humidity, wind_speed, population_density]
        or None if critical files are missing.
    """
    logger.info(f"\n--- Merging year {year} ---")

    # ── LST (required) ──
    lst_path = find_csv(input_dir, f"lst_{year}.csv")
    if lst_path is None:
        logger.error(f"  MISSING: lst_{year}.csv — skipping year {year}")
        return None
    lst_df = load_csv(lst_path, expected_columns=["cell_code", "lst"])

    # Handle case where column is named 'mean' instead of 'lst'
    if "mean" in lst_df.columns and "lst" not in lst_df.columns:
        lst_df = lst_df.rename(columns={"mean": "lst"})

    merged = lst_df[["cell_code", "lst"]].copy()

    # ── Spectral Indices (required) ──
    indices_path = find_csv(input_dir, f"spectral_indices_{year}.csv")
    if indices_path is None:
        logger.error(
            f"  MISSING: spectral_indices_{year}.csv — skipping year {year}"
        )
        return None
    indices_df = load_csv(
        indices_path, expected_columns=["cell_code", "ndvi", "ndbi", "ndwi"]
    )

    merged = merged.merge(
        indices_df[["cell_code", "ndvi", "ndbi", "ndwi"]],
        on="cell_code",
        how="inner",
    )
    logger.info(f"  After LST + indices join: {len(merged)} cells")

    # ── Tree Canopy (static, optional but important) ──
    if tree_canopy_df is not None:
        merged = merged.merge(
            tree_canopy_df[["cell_code", "tree_canopy_frac"]],
            on="cell_code",
            how="left",
        )
        logger.info(f"  After tree canopy join: {len(merged)} cells")
    else:
        merged["tree_canopy_frac"] = np.nan
        logger.warning("  Tree canopy data not available — column filled with NaN")

    # ── ERA5 Climate (optional — Phase 2) ──
    era5_path = find_csv(input_dir, f"era5_{year}.csv")
    if era5_path:
        era5_df = load_csv(
            era5_path, expected_columns=["cell_code", "humidity", "wind_speed"]
        )
        merged = merged.merge(
            era5_df[["cell_code", "humidity", "wind_speed"]],
            on="cell_code",
            how="left",
        )
        logger.info(f"  After ERA5 join: {len(merged)} cells")
    else:
        merged["humidity"] = np.nan
        merged["wind_speed"] = np.nan
        logger.info(f"  ERA5 data not found for {year} — columns filled with NaN")

    # ── Population (optional — Phase 2) ──
    pop_path = find_csv(input_dir, f"population_{year}.csv")
    if pop_path:
        pop_df = load_csv(
            pop_path, expected_columns=["cell_code", "population_density"]
        )
        merged = merged.merge(
            pop_df[["cell_code", "population_density"]],
            on="cell_code",
            how="left",
        )
        logger.info(f"  After population join: {len(merged)} cells")
    else:
        merged["population_density"] = np.nan
        logger.info(f"  Population data not found for {year} — column filled with NaN")

    # Add year column
    merged["year"] = year

    return merged


# ══════════════════════════════════════════════════════════════
# Validation
# ══════════════════════════════════════════════════════════════


def validate_dataframe(df: pd.DataFrame) -> None:
    """
    Run quality checks on the merged feature matrix.

    Logs warnings for data quality issues but does NOT drop rows —
    the user should investigate and decide.
    """
    logger.info("\n" + "=" * 60)
    logger.info("DATA QUALITY REPORT")
    logger.info("=" * 60)

    total_rows = len(df)
    logger.info(f"Total rows: {total_rows}")
    logger.info(f"Years: {sorted(df['year'].unique())}")
    logger.info(f"Unique cells: {df['cell_code'].nunique()}")

    # ── Null rate per column ──
    logger.info("\nNull rates:")
    for col in df.columns:
        if col in ("cell_code", "year"):
            continue
        null_count = df[col].isna().sum()
        null_pct = (null_count / total_rows) * 100
        status = "⚠ WARNING" if null_pct > 10 else "✓"
        logger.info(f"  {col:25s}: {null_count:6d} nulls ({null_pct:5.1f}%) {status}")

    # ── Value range checks ──
    range_checks = {
        "lst":              (20, 55, "°C — expected for Pune hot season"),
        "ndvi":             (-1, 1, "— normalized index"),
        "ndbi":             (-1, 1, "— normalized index"),
        "ndwi":             (-1, 1, "— normalized index"),
        "tree_canopy_frac": (0, 1, "— fraction"),
        "humidity":         (0, 100, "% — relative humidity"),
        "wind_speed":       (0, 30, "m/s"),
        "population_density": (0, 100_000, "persons/km²"),
    }

    logger.info("\nValue ranges:")
    for col, (low, high, unit) in range_checks.items():
        if col not in df.columns or df[col].isna().all():
            continue
        actual_min = df[col].min()
        actual_max = df[col].max()
        out_of_range = ((df[col] < low) | (df[col] > high)).sum()
        status = "⚠" if out_of_range > 0 else "✓"
        logger.info(
            f"  {col:25s}: [{actual_min:8.2f}, {actual_max:8.2f}] "
            f"expected [{low}, {high}] {unit}  "
            f"({out_of_range} out-of-range) {status}"
        )

    # ── Per-year cell counts ──
    logger.info("\nCells per year:")
    for year, group in df.groupby("year"):
        logger.info(f"  {year}: {len(group)} cells")

    logger.info("=" * 60)


# ══════════════════════════════════════════════════════════════
# Main Pipeline
# ══════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Merge GEE-exported CSVs into a unified training set."
    )
    parser.add_argument(
        "--input-dir", type=Path, required=True,
        help="Directory containing GEE CSV exports (downloaded from Drive)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("../ml/data/training_set.csv"),
        help="Output path for the merged training set (default: ../ml/data/training_set.csv)",
    )
    parser.add_argument(
        "--years", nargs="+", type=int, default=DEFAULT_YEARS,
        help=f"Years to merge (default: {DEFAULT_YEARS})",
    )
    parser.add_argument(
        "--skip-validation", action="store_true",
        help="Skip data quality validation",
    )
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        logger.error(f"Input directory not found: {args.input_dir}")
        sys.exit(1)

    logger.info(f"Input directory:  {args.input_dir.resolve()}")
    logger.info(f"Output file:      {args.output.resolve()}")
    logger.info(f"Years to merge:   {args.years}")

    # ── Load static layers ──
    tree_canopy_df = None
    tree_path = find_csv(args.input_dir, "tree_canopy_*.csv")
    if tree_path:
        tree_canopy_df = load_csv(
            tree_path, expected_columns=["cell_code", "tree_canopy_frac"]
        )
        # Handle 'mean' column name
        if "mean" in tree_canopy_df.columns and "tree_canopy_frac" not in tree_canopy_df.columns:
            tree_canopy_df = tree_canopy_df.rename(columns={"mean": "tree_canopy_frac"})
    else:
        logger.warning("Tree canopy CSV not found — proceeding without it")

    # ── Merge each year ──
    all_years = []
    for year in args.years:
        year_df = merge_year(year, args.input_dir, tree_canopy_df)
        if year_df is not None:
            all_years.append(year_df)

    if not all_years:
        logger.error("No years were successfully merged. Check input files.")
        sys.exit(1)

    # ── Concatenate all years ──
    merged = pd.concat(all_years, ignore_index=True)

    # Reorder columns for clarity
    column_order = [
        "cell_code", "year",
        "lst", "ndvi", "ndbi", "ndwi", "tree_canopy_frac",
        "humidity", "wind_speed", "population_density",
    ]
    # Only include columns that exist
    column_order = [c for c in column_order if c in merged.columns]
    merged = merged[column_order]

    logger.info(f"\nFinal merged dataset: {len(merged)} rows × {len(merged.columns)} columns")

    # ── Validate ──
    if not args.skip_validation:
        validate_dataframe(merged)

    # ── Save ──
    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.output, index=False, float_format="%.6f")

    file_size_mb = args.output.stat().st_size / (1024 * 1024)
    logger.info(f"\nSaved training set to: {args.output.resolve()} ({file_size_mb:.1f} MB)")

    # ── Summary ──
    logger.info("\n" + "=" * 60)
    logger.info("MERGE COMPLETE — SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Total cells:    {merged['cell_code'].nunique()}")
    logger.info(f"  Total years:    {merged['year'].nunique()}")
    logger.info(f"  Total rows:     {len(merged)}")
    logger.info(f"  Output file:    {args.output.resolve()}")
    logger.info(f"  File size:      {file_size_mb:.1f} MB")
    logger.info(
        f"\n  ML target variable:  lst (observed)"
        f"\n  ML features:         ndvi, ndbi, ndwi, tree_canopy_frac"
        f"\n  HVI indicators:      humidity, wind_speed, population_density"
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
