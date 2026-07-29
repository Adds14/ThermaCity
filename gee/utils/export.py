"""
ThermaCity — GEE Export & Reduction Utilities

Provides the SINGLE canonical reduction and export pattern used by
every extraction script. This guarantees mathematical consistency:
all bands are reduced to the same grid, with the same reducer,
at the same scale and CRS.

Core contract:
  - Reducer:  ee.Reducer.mean()
  - Scale:    100 meters
  - CRS:     EPSG:4326
  - Grid:     The shared FeatureCollection from geometry.get_analysis_grid()

Usage:
    from utils.export import reduce_to_grid, export_to_drive, wait_for_tasks

    reduced = reduce_to_grid(composite, grid, output_name="lst")
    task = export_to_drive(reduced, "lst_2023", folder="ThermaCity_Exports",
                           selectors=["cell_code", "lst"])
    wait_for_tasks([task])
"""

import logging
import time

import ee

logger = logging.getLogger(__name__)

# ── Pipeline Constants (shared across ALL extraction scripts) ─
REDUCE_SCALE = 100          # meters — matches grid cell size
REDUCE_CRS = "EPSG:4326"   # WGS84

HOT_SEASON_START_MONTH = 3  # March
HOT_SEASON_END_MONTH = 6    # June (inclusive)

DEFAULT_YEARS = list(range(2021, 2027))  # 2021–2026

DRIVE_FOLDER = "ThermaCity_Exports"  # Google Drive folder for CSV exports


# ══════════════════════════════════════════════════════════════
# Canonical Reduction
# ══════════════════════════════════════════════════════════════


def reduce_to_grid(
    image: ee.Image,
    grid: ee.FeatureCollection,
    output_name: str | None = None,
) -> ee.FeatureCollection:
    """
    Reduce an image to grid-cell means using ee.Reducer.mean().

    THIS IS THE ONLY REDUCTION FUNCTION IN THE PIPELINE.
    All extraction scripts must use this function (not call
    reduceRegions directly) to guarantee spatial consistency.

    Args:
        image:       ee.Image to reduce (single or multi-band).
        grid:        ee.FeatureCollection of 100×100 m grid cells.
        output_name: For single-band images, rename the 'mean' output
                     property to this name (e.g., 'lst'). For multi-band
                     images, leave as None — GEE names outputs by band.

    Returns:
        ee.FeatureCollection where each feature has the original grid
        properties plus the reduced band values.
    """
    reduced = image.reduceRegions(
        collection=grid,
        reducer=ee.Reducer.mean(),
        scale=REDUCE_SCALE,
        crs=REDUCE_CRS,
    )

    # For single-band images, GEE names the output property 'mean'.
    # Rename it to a meaningful name for downstream joins.
    if output_name:
        reduced = reduced.map(
            lambda f: f.set(output_name, f.get("mean"))
        )

    return reduced


# ══════════════════════════════════════════════════════════════
# Drive Export
# ══════════════════════════════════════════════════════════════


def export_to_drive(
    feature_collection: ee.FeatureCollection,
    description: str,
    folder: str = DRIVE_FOLDER,
    selectors: list[str] | None = None,
) -> ee.batch.Task:
    """
    Export a FeatureCollection to Google Drive as CSV.

    Args:
        feature_collection: The reduced FeatureCollection to export.
        description:        Export task name and file prefix (e.g., 'lst_2023').
        folder:             Google Drive folder name.
        selectors:          Column names to include in the CSV.
                            Always include 'cell_code'. Omit '.geo' to
                            exclude geometry (keeps CSVs small).

    Returns:
        ee.batch.Task — the started export task.
    """
    export_params = {
        "collection": feature_collection,
        "description": description,
        "folder": folder,
        "fileNamePrefix": description,
        "fileFormat": "CSV",
    }

    if selectors:
        export_params["selectors"] = selectors

    task = ee.batch.Export.table.toDrive(**export_params)
    task.start()

    logger.info(f"  Export task started: {description} → Drive/{folder}/")
    return task


# ══════════════════════════════════════════════════════════════
# Task Management
# ══════════════════════════════════════════════════════════════


def wait_for_tasks(
    tasks: list[ee.batch.Task],
    poll_interval_s: int = 30,
) -> dict[str, str]:
    """
    Block until all GEE export tasks complete.

    Args:
        tasks:           List of ee.batch.Task objects to monitor.
        poll_interval_s: Seconds between status checks.

    Returns:
        Dict mapping task description → final state ('COMPLETED' or 'FAILED').

    Raises:
        RuntimeError if any task fails.
    """
    if not tasks:
        return {}

    task_map = {t.status()["description"]: t for t in tasks}
    total = len(task_map)
    results = {}

    logger.info(f"Waiting for {total} export task(s) to complete...")

    while task_map:
        time.sleep(poll_interval_s)

        completed_keys = []
        for desc, task in task_map.items():
            status = task.status()
            state = status.get("state", "UNKNOWN")

            if state == "COMPLETED":
                logger.info(f"  ✓ {desc} — COMPLETED")
                results[desc] = "COMPLETED"
                completed_keys.append(desc)

            elif state == "FAILED":
                error = status.get("error_message", "Unknown error")
                logger.error(f"  ✗ {desc} — FAILED: {error}")
                results[desc] = f"FAILED: {error}"
                completed_keys.append(desc)

            elif state == "CANCEL_REQUESTED":
                logger.warning(f"  ⊘ {desc} — CANCELLED")
                results[desc] = "CANCELLED"
                completed_keys.append(desc)

            else:
                # READY, RUNNING, etc.
                pass

        for key in completed_keys:
            del task_map[key]

        remaining = len(task_map)
        if remaining > 0:
            done = total - remaining
            logger.info(
                f"  Progress: {done}/{total} complete, "
                f"{remaining} still running..."
            )

    # Check for failures
    failures = {k: v for k, v in results.items() if v.startswith("FAILED")}
    if failures:
        msg = "\n".join(f"  - {k}: {v}" for k, v in failures.items())
        raise RuntimeError(f"The following GEE export tasks failed:\n{msg}")

    logger.info(f"All {total} export task(s) completed successfully.")
    return results


# ══════════════════════════════════════════════════════════════
# Date Helpers
# ══════════════════════════════════════════════════════════════


def hot_season_date_range(year: int) -> tuple[str, str]:
    """
    Return (start_date, end_date) strings for Pune's hot season.

    The hot season is defined as March 1 – June 30, which captures
    peak UHI conditions before the monsoon onset.

    Returns:
        Tuple of ISO date strings, e.g. ('2023-03-01', '2023-06-30').
    """
    return (
        f"{year}-{HOT_SEASON_START_MONTH:02d}-01",
        f"{year}-{HOT_SEASON_END_MONTH:02d}-30",
    )
