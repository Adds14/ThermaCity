"""
ThermaCity — Grid Router

Endpoints for querying the 100×100 m spatial grid.
Returns GeoJSON FeatureCollections for map rendering.

Routes:
  GET /grid           — All grid cells as GeoJSON (with bbox filter + year)
  GET /grid/{cell_id} — Single cell detail with historical features
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.spatial_grid import SpatialGrid
from app.models.environmental_features import EnvironmentalFeature
from app.services.geojson_builder import build_feature_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/grid", tags=["Grid"])


@router.get("")
async def get_grid(
    year: int = Query(2024, ge=2020, le=2030, description="Data year"),
    bbox: str | None = Query(
        None,
        description="Bounding box filter: 'min_lng,min_lat,max_lng,max_lat'",
        example="73.80,18.45,73.95,18.60",
    ),
    limit: int = Query(5000, ge=1, le=50000, description="Max cells to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch grid cells as a GeoJSON FeatureCollection.

    Each feature includes the cell's environmental data and HVI score
    for the requested year. Use the `bbox` parameter to filter by map
    viewport — essential for frontend performance with 30k+ cells.
    """
    # Build query: join grid with features for the requested year
    stmt = (
        select(SpatialGrid, EnvironmentalFeature)
        .outerjoin(
            EnvironmentalFeature,
            (SpatialGrid.id == EnvironmentalFeature.grid_id)
            & (EnvironmentalFeature.year == year),
        )
    )

    # Apply bounding box filter using PostGIS ST_Intersects
    if bbox:
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError("Expected 4 values")
            min_lng, min_lat, max_lng, max_lat = parts
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid bbox format. Expected 'min_lng,min_lat,max_lng,max_lat': {e}",
            )

        bbox_wkt = (
            f"SRID=4326;POLYGON(("
            f"{min_lng} {min_lat},"
            f"{max_lng} {min_lat},"
            f"{max_lng} {max_lat},"
            f"{min_lng} {max_lat},"
            f"{min_lng} {min_lat}))"
        )

        from geoalchemy2 import WKTElement
        bbox_geom = WKTElement(bbox_wkt, srid=4326)
        stmt = stmt.where(SpatialGrid.geom.ST_Intersects(bbox_geom))

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    # Build GeoJSON features
    features = []
    for grid_cell, env_features in rows:
        properties = {
            "cell_id": grid_cell.id,
            "cell_code": grid_cell.cell_code,
            "ward_id": grid_cell.ward_id,
            "year": year,
        }

        if env_features:
            properties.update({
                "lst_observed": env_features.lst_observed,
                "ndvi": env_features.ndvi,
                "ndbi": env_features.ndbi,
                "ndwi": env_features.ndwi,
                "tree_canopy_frac": env_features.tree_canopy_frac,
                "humidity": env_features.humidity,
                "wind_speed": env_features.wind_speed,
                "population_density": env_features.population_density,
                "lst_predicted": env_features.lst_predicted,
                "hvi_score": env_features.hvi_score,
                "hvi_tier": env_features.hvi_tier,
            })

        features.append({
            "type": "Feature",
            "geometry": _wkb_to_geojson(grid_cell.geom),
            "properties": properties,
        })

    return {
        "type": "FeatureCollection",
        "metadata": {"year": year, "count": len(features)},
        "features": features,
    }


@router.get("/{cell_id}")
async def get_grid_cell(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed data for a single grid cell, including all years.

    Returns the cell geometry, ward info, and a historical array
    of environmental features from 2021–2026.
    """
    # Fetch cell with all feature years
    stmt = (
        select(SpatialGrid)
        .where(SpatialGrid.id == cell_id)
        .options(selectinload(SpatialGrid.features))
    )
    result = await db.execute(stmt)
    cell = result.scalar_one_or_none()

    if not cell:
        raise HTTPException(status_code=404, detail=f"Grid cell {cell_id} not found")

    # Build historical features list
    history = []
    for feat in sorted(cell.features, key=lambda f: f.year):
        history.append({
            "year": feat.year,
            "lst_observed": feat.lst_observed,
            "lst_predicted": feat.lst_predicted,
            "ndvi": feat.ndvi,
            "ndbi": feat.ndbi,
            "ndwi": feat.ndwi,
            "tree_canopy_frac": feat.tree_canopy_frac,
            "humidity": feat.humidity,
            "wind_speed": feat.wind_speed,
            "population_density": feat.population_density,
            "hvi_score": feat.hvi_score,
            "hvi_tier": feat.hvi_tier,
        })

    return {
        "id": cell.id,
        "cell_code": cell.cell_code,
        "ward_id": cell.ward_id,
        "geometry": _wkb_to_geojson(cell.geom),
        "features_by_year": history,
    }


def _wkb_to_geojson(geom) -> dict | None:
    """Convert a GeoAlchemy2 WKBElement to a GeoJSON geometry dict."""
    if geom is None:
        return None
    try:
        from geoalchemy2.shape import to_shape
        from shapely.geometry import mapping
        return mapping(to_shape(geom))
    except Exception:
        return None
