"""
ThermaCity — Scenario Simulator Router

"What-if" analytics endpoint. Allows urban planners to modify environmental
features (like adding tree canopy) and see the predicted change in temperature
and Heat Vulnerability Score.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.main import get_ml_predictor
from app.models.environmental_features import EnvironmentalFeature
from app.models.spatial_grid import SpatialGrid
from app.schemas.scenario import ScenarioRequest, ScenarioResult
from app.services.hvi_calculator import HVICalculator
from app.services.ml_predictor import MLPredictor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenario", tags=["Scenario Simulator"])


@router.post("/simulate", response_model=list[ScenarioResult])
async def simulate_scenario(
    request: ScenarioRequest,
    db: AsyncSession = Depends(get_db),
    ml_predictor: MLPredictor | None = Depends(get_ml_predictor),
):
    """
    Run a scenario simulation on one or more grid cells.

    This does NOT modify the database. It:
    1. Fetches current environmental features for the requested cells.
    2. Applies the requested feature deltas (e.g. tree_canopy_delta = +0.2).
    3. Runs the Random Forest model to predict new Land Surface Temperatures.
    4. Runs the HVI calculator to compute new vulnerability scores.
    5. Returns the before/after comparisons.
    """
    if not ml_predictor:
        raise HTTPException(
            status_code=503,
            detail="Scenario simulator unavailable. ML model failed to load.",
        )

    # 1. Fetch current features for the requested cells and year
    stmt = (
        select(SpatialGrid, EnvironmentalFeature)
        .join(EnvironmentalFeature, SpatialGrid.id == EnvironmentalFeature.grid_id)
        .where(
            SpatialGrid.id.in_(request.cell_ids),
            EnvironmentalFeature.year == request.year,
        )
    )
    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for the requested cells in year {request.year}",
        )

    # Fetch ALL cells for the year to perform proper Min-Max normalization for HVI
    all_stmt = select(EnvironmentalFeature).where(
        EnvironmentalFeature.year == request.year
    )
    all_result = await db.execute(all_stmt)
    all_features = all_result.scalars().all()
    
    # We need to build a batch for HVI calculation that includes our modified cells
    # and all the unmodified cells, so the normalization is accurate relative to the whole city.
    
    # Build a lookup for unmodified features
    feature_dicts = []
    cell_to_dict_idx = {}
    
    for idx, f in enumerate(all_features):
        d = {
            "grid_id": f.grid_id,
            "lst_predicted": f.lst_predicted,
            "population_density": f.population_density,
            "tree_canopy_frac": f.tree_canopy_frac,
            "humidity": f.humidity,
            "wind_speed": f.wind_speed,
        }
        feature_dicts.append(d)
        cell_to_dict_idx[f.grid_id] = idx

    results = []

    # 2 & 3: Apply deltas and run ML prediction for requested cells
    for grid, env in rows:
        # Original values
        orig_lst = env.lst_predicted
        orig_hvi = env.hvi_score
        orig_tier = env.hvi_tier
        
        # Apply deltas (ensuring bounds)
        sim_ndvi = max(-1.0, min(1.0, (env.ndvi or 0) + request.ndvi_delta))
        sim_ndbi = max(-1.0, min(1.0, (env.ndbi or 0) + request.ndbi_delta))
        sim_ndwi = max(-1.0, min(1.0, (env.ndwi or 0) + request.ndwi_delta))
        sim_canopy = max(0.0, min(1.0, (env.tree_canopy_frac or 0) + request.tree_canopy_delta))

        # Predict new LST
        ml_features = {
            "ndvi": sim_ndvi,
            "ndbi": sim_ndbi,
            "ndwi": sim_ndwi,
            "tree_canopy_frac": sim_canopy,
        }
        sim_lst = ml_predictor.predict_lst(ml_features)
        
        # Update the batch dict for HVI calculation
        idx = cell_to_dict_idx[grid.id]
        feature_dicts[idx]["lst_predicted"] = sim_lst
        feature_dicts[idx]["tree_canopy_frac"] = sim_canopy

        # Prepare base result (HVI will be populated after batch calc)
        results.append({
            "cell_id": grid.id,
            "cell_code": grid.cell_code,
            "original_lst": round(orig_lst, 2) if orig_lst else None,
            "simulated_lst": round(sim_lst, 2),
            "lst_delta": round(sim_lst - orig_lst, 2) if orig_lst else None,
            "original_hvi": orig_hvi,
            "original_tier": orig_tier,
            "_dict_idx": idx # internal ref
        })

    # 4. Run HVI calculator for the whole city to get properly normalized scores
    # We pass the modified dicts
    hvi_results = HVICalculator.compute_batch(feature_dicts, settings.hvi_weight_dict)
    
    # 5. Populate HVI fields into our results
    final_results = []
    for r in results:
        idx = r.pop("_dict_idx")
        sim_hvi_info = hvi_results[idx]
        
        sim_hvi = sim_hvi_info["hvi_score"]
        sim_tier = sim_hvi_info["hvi_tier"]
        orig_hvi = r["original_hvi"]
        
        final_results.append(ScenarioResult(
            cell_id=r["cell_id"],
            cell_code=r["cell_code"],
            original_lst=r["original_lst"],
            simulated_lst=r["simulated_lst"],
            lst_delta=r["lst_delta"],
            original_hvi=round(orig_hvi, 2) if orig_hvi is not None else None,
            simulated_hvi=sim_hvi,
            hvi_delta=round(sim_hvi - orig_hvi, 2) if orig_hvi is not None else None,
            original_tier=r["original_tier"],
            simulated_tier=sim_tier
        ))

    return final_results
