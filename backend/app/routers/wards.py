"""
ThermaCity — Wards Router

Endpoints for ward-level aggregation and rankings.

Routes:
  GET /wards              — Ward rankings sorted by HVI (most dangerous first)
  GET /wards/geometries   — Ward boundary polygons as GeoJSON FeatureCollection
  GET /wards/{ward_id}    — Single ward deep-dive with cell breakdown
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.spatial_grid import SpatialGrid
from app.models.environmental_features import EnvironmentalFeature
from app.models.ward_boundary import WardBoundary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wards", tags=["Wards"])


@router.get("")
async def get_ward_rankings(
    year: int = Query(2024, ge=2020, le=2030, description="Data year"),
    sort: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    db: AsyncSession = Depends(get_db),
):
    """
    Ward-level HVI rankings.

    Aggregates grid-cell scores by ward to produce a sortable ranking.
    This tells the commissioner which wards need intervention most.
    """
    sort_func = desc if sort == "desc" else lambda x: x

    stmt = (
        select(
            WardBoundary.id.label("ward_id"),
            WardBoundary.ward_name,
            WardBoundary.ward_code,
            func.avg(EnvironmentalFeature.hvi_score).label("avg_hvi"),
            func.max(EnvironmentalFeature.hvi_score).label("max_hvi"),
            func.min(EnvironmentalFeature.hvi_score).label("min_hvi"),
            func.count(EnvironmentalFeature.id).label("cell_count"),
            func.avg(EnvironmentalFeature.lst_observed).label("avg_lst"),
            func.avg(EnvironmentalFeature.tree_canopy_frac).label("avg_canopy"),
            func.avg(EnvironmentalFeature.population_density).label("avg_pop_density"),
        )
        .join(SpatialGrid, SpatialGrid.ward_id == WardBoundary.id)
        .join(
            EnvironmentalFeature,
            (EnvironmentalFeature.grid_id == SpatialGrid.id)
            & (EnvironmentalFeature.year == year),
        )
        .where(EnvironmentalFeature.hvi_score.isnot(None))
        .group_by(WardBoundary.id, WardBoundary.ward_name, WardBoundary.ward_code)
        .order_by(sort_func(func.avg(EnvironmentalFeature.hvi_score)))
    )

    result = await db.execute(stmt)
    rows = result.all()

    rankings = []
    for rank, row in enumerate(rows, 1):
        # Determine dominant tier based on average
        avg = float(row.avg_hvi) if row.avg_hvi else 0
        if avg >= 76:
            tier = "Emergency"
        elif avg >= 51:
            tier = "Stressed"
        elif avg >= 26:
            tier = "Caution"
        else:
            tier = "Heat-Safe"

        rankings.append({
            "rank": rank,
            "ward_id": row.ward_id,
            "ward_name": row.ward_name,
            "ward_code": row.ward_code,
            "avg_hvi": round(avg, 2),
            "max_hvi": round(float(row.max_hvi), 2) if row.max_hvi else None,
            "min_hvi": round(float(row.min_hvi), 2) if row.min_hvi else None,
            "dominant_tier": tier,
            "cell_count": row.cell_count,
            "avg_lst_celsius": round(float(row.avg_lst), 1) if row.avg_lst else None,
            "avg_canopy_pct": (
                round(float(row.avg_canopy) * 100, 1) if row.avg_canopy else None
            ),
            "avg_pop_density": (
                round(float(row.avg_pop_density), 0) if row.avg_pop_density else None
            ),
        })

    return {
        "year": year,
        "total_wards": len(rankings),
        "rankings": rankings,
    }


@router.get("/geometries")
async def get_ward_geometries(
    year: int = Query(2024, ge=2020, le=2030, description="Data year"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return all ward boundaries as a GeoJSON FeatureCollection.

    Each feature includes the ward polygon geometry and aggregate HVI
    stats for the requested year — ready for direct rendering on a
    Leaflet map with tier-based colouring.
    """
    stmt = (
        select(
            WardBoundary.id.label("ward_id"),
            WardBoundary.ward_name,
            WardBoundary.geom,
            func.avg(EnvironmentalFeature.hvi_score).label("avg_hvi"),
            func.count(EnvironmentalFeature.id).label("cell_count"),
            func.avg(EnvironmentalFeature.lst_observed).label("avg_lst"),
        )
        .join(SpatialGrid, SpatialGrid.ward_id == WardBoundary.id)
        .join(
            EnvironmentalFeature,
            (EnvironmentalFeature.grid_id == SpatialGrid.id)
            & (EnvironmentalFeature.year == year),
        )
        .where(EnvironmentalFeature.hvi_score.isnot(None))
        .group_by(WardBoundary.id, WardBoundary.ward_name, WardBoundary.geom)
        .order_by(desc(func.avg(EnvironmentalFeature.hvi_score)))
    )

    result = await db.execute(stmt)
    rows = result.all()

    features = []
    for row in rows:
        avg = float(row.avg_hvi) if row.avg_hvi else 0
        if avg >= 76:
            tier = "Emergency"
        elif avg >= 51:
            tier = "Stressed"
        elif avg >= 26:
            tier = "Caution"
        else:
            tier = "Heat-Safe"

        ward_geom = None
        if row.geom:
            try:
                from geoalchemy2.shape import to_shape
                from shapely.geometry import mapping
                ward_geom = mapping(to_shape(row.geom))
            except Exception:
                pass

        if not ward_geom:
            continue

        features.append({
            "type": "Feature",
            "geometry": ward_geom,
            "properties": {
                "ward_id": row.ward_id,
                "ward_name": row.ward_name,
                "avg_hvi": round(avg, 2),
                "hvi_tier": tier,
                "cell_count": row.cell_count,
                "avg_lst": round(float(row.avg_lst), 1) if row.avg_lst else None,
            },
        })

    return {
        "type": "FeatureCollection",
        "metadata": {"year": year, "count": len(features)},
        "features": features,
    }


@router.get("/{ward_id}")
async def get_ward_detail(
    ward_id: int,
    year: int = Query(2024, ge=2020, le=2030, description="Data year"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detailed breakdown for a single ward.

    Returns the ward's boundary geometry, aggregate stats, tier distribution,
    and a list of its hottest grid cells — so planners can pinpoint
    exactly where interventions are needed within the ward.
    """
    # Fetch ward info
    ward_stmt = select(WardBoundary).where(WardBoundary.id == ward_id)
    ward_result = await db.execute(ward_stmt)
    ward = ward_result.scalar_one_or_none()

    if not ward:
        raise HTTPException(status_code=404, detail=f"Ward {ward_id} not found")

    # Aggregate stats for this ward
    stats_stmt = (
        select(
            func.count(EnvironmentalFeature.id).label("cell_count"),
            func.avg(EnvironmentalFeature.hvi_score).label("avg_hvi"),
            func.max(EnvironmentalFeature.hvi_score).label("max_hvi"),
            func.min(EnvironmentalFeature.hvi_score).label("min_hvi"),
            func.avg(EnvironmentalFeature.lst_observed).label("avg_lst"),
            func.avg(EnvironmentalFeature.tree_canopy_frac).label("avg_canopy"),
            func.avg(EnvironmentalFeature.humidity).label("avg_humidity"),
            func.avg(EnvironmentalFeature.wind_speed).label("avg_wind"),
            func.avg(EnvironmentalFeature.population_density).label("avg_pop"),
        )
        .join(SpatialGrid, SpatialGrid.id == EnvironmentalFeature.grid_id)
        .where(
            SpatialGrid.ward_id == ward_id,
            EnvironmentalFeature.year == year,
            EnvironmentalFeature.hvi_score.isnot(None),
        )
    )
    stats_result = await db.execute(stats_stmt)
    stats = stats_result.one()

    # Tier distribution within this ward
    tier_stmt = (
        select(
            EnvironmentalFeature.hvi_tier,
            func.count(EnvironmentalFeature.id).label("count"),
        )
        .join(SpatialGrid, SpatialGrid.id == EnvironmentalFeature.grid_id)
        .where(
            SpatialGrid.ward_id == ward_id,
            EnvironmentalFeature.year == year,
            EnvironmentalFeature.hvi_tier.isnot(None),
        )
        .group_by(EnvironmentalFeature.hvi_tier)
    )
    tier_result = await db.execute(tier_stmt)
    tier_distribution = {t.hvi_tier: t.count for t in tier_result.all()}

    # Top 10 hottest cells in this ward (for targeted intervention)
    hotspots_stmt = (
        select(
            SpatialGrid.cell_code,
            SpatialGrid.id.label("cell_id"),
            EnvironmentalFeature.hvi_score,
            EnvironmentalFeature.hvi_tier,
            EnvironmentalFeature.lst_observed,
            EnvironmentalFeature.tree_canopy_frac,
        )
        .join(SpatialGrid, SpatialGrid.id == EnvironmentalFeature.grid_id)
        .where(
            SpatialGrid.ward_id == ward_id,
            EnvironmentalFeature.year == year,
            EnvironmentalFeature.hvi_score.isnot(None),
        )
        .order_by(desc(EnvironmentalFeature.hvi_score))
        .limit(10)
    )
    hotspots_result = await db.execute(hotspots_stmt)
    hotspots = [
        {
            "cell_id": h.cell_id,
            "cell_code": h.cell_code,
            "hvi_score": round(float(h.hvi_score), 2),
            "hvi_tier": h.hvi_tier,
            "lst_celsius": round(float(h.lst_observed), 1) if h.lst_observed else None,
            "canopy_pct": (
                round(float(h.tree_canopy_frac) * 100, 1)
                if h.tree_canopy_frac
                else None
            ),
        }
        for h in hotspots_result.all()
    ]

    # Build ward geometry GeoJSON
    ward_geom = None
    if ward.geom:
        try:
            from geoalchemy2.shape import to_shape
            from shapely.geometry import mapping
            ward_geom = mapping(to_shape(ward.geom))
        except Exception:
            pass

    return {
        "ward_id": ward.id,
        "ward_name": ward.ward_name,
        "ward_code": ward.ward_code,
        "year": year,
        "geometry": ward_geom,
        "summary": {
            "cell_count": stats.cell_count,
            "avg_hvi": round(float(stats.avg_hvi), 2) if stats.avg_hvi else None,
            "max_hvi": round(float(stats.max_hvi), 2) if stats.max_hvi else None,
            "min_hvi": round(float(stats.min_hvi), 2) if stats.min_hvi else None,
            "avg_lst_celsius": round(float(stats.avg_lst), 1) if stats.avg_lst else None,
            "avg_canopy_pct": (
                round(float(stats.avg_canopy) * 100, 1) if stats.avg_canopy else None
            ),
            "avg_humidity_pct": (
                round(float(stats.avg_humidity), 1) if stats.avg_humidity else None
            ),
            "avg_wind_ms": (
                round(float(stats.avg_wind), 1) if stats.avg_wind else None
            ),
            "avg_pop_density": (
                round(float(stats.avg_pop), 0) if stats.avg_pop else None
            ),
        },
        "tier_distribution": tier_distribution,
        "top_hotspots": hotspots,
    }
