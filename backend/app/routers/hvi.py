"""
ThermaCity — HVI Router

Endpoints for Heat Vulnerability Score analytics.

Routes:
  GET /hvi/summary    — City-wide HVI statistics for a year
  GET /hvi/temporal   — Multi-year HVI trend data
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.environmental_features import EnvironmentalFeature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hvi", tags=["Heat Vulnerability"])


@router.get("/summary")
async def hvi_summary(
    year: int = Query(2024, ge=2020, le=2030, description="Data year"),
    db: AsyncSession = Depends(get_db),
):
    """
    City-wide Heat Vulnerability Score summary for a given year.

    Returns aggregate statistics and the tier distribution — how many
    grid cells fall into each risk tier. This powers the dashboard's
    headline statistics panel.
    """
    # Aggregate HVI statistics
    stmt = select(
        func.count(EnvironmentalFeature.id).label("total_cells"),
        func.avg(EnvironmentalFeature.hvi_score).label("avg_score"),
        func.max(EnvironmentalFeature.hvi_score).label("max_score"),
        func.min(EnvironmentalFeature.hvi_score).label("min_score"),
        func.stddev(EnvironmentalFeature.hvi_score).label("std_score"),
    ).where(
        EnvironmentalFeature.year == year,
        EnvironmentalFeature.hvi_score.isnot(None),
    )

    result = await db.execute(stmt)
    row = result.one()

    # Tier distribution
    tier_stmt = select(
        EnvironmentalFeature.hvi_tier,
        func.count(EnvironmentalFeature.id).label("count"),
    ).where(
        EnvironmentalFeature.year == year,
        EnvironmentalFeature.hvi_tier.isnot(None),
    ).group_by(EnvironmentalFeature.hvi_tier)

    tier_result = await db.execute(tier_stmt)
    tier_distribution = {t.hvi_tier: t.count for t in tier_result.all()}

    # Estimate exposed population in high-risk zones
    population_stmt = select(
        func.sum(EnvironmentalFeature.population_density).label("total_pop_density"),
    ).where(
        EnvironmentalFeature.year == year,
        EnvironmentalFeature.hvi_tier.in_(["Stressed", "Emergency"]),
    )
    pop_result = await db.execute(population_stmt)
    pop_row = pop_result.one()

    return {
        "year": year,
        "total_cells": row.total_cells,
        "avg_score": round(float(row.avg_score), 2) if row.avg_score else None,
        "max_score": round(float(row.max_score), 2) if row.max_score else None,
        "min_score": round(float(row.min_score), 2) if row.min_score else None,
        "std_score": round(float(row.std_score), 2) if row.std_score else None,
        "tier_distribution": tier_distribution,
        "high_risk_cells": (
            tier_distribution.get("Stressed", 0)
            + tier_distribution.get("Emergency", 0)
        ),
        "estimated_exposed_pop_density": (
            round(float(pop_row.total_pop_density), 0)
            if pop_row.total_pop_density
            else None
        ),
    }


@router.get("/temporal")
async def hvi_temporal(
    ward_id: int | None = Query(None, description="Filter by ward ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Multi-year HVI trend data (2021–2026).

    Returns per-year averages and tier distributions for the temporal
    slider on the dashboard. Can be filtered by ward.
    """
    # Base query
    base = select(
        EnvironmentalFeature.year,
        func.avg(EnvironmentalFeature.hvi_score).label("avg_hvi"),
        func.max(EnvironmentalFeature.hvi_score).label("max_hvi"),
        func.min(EnvironmentalFeature.hvi_score).label("min_hvi"),
        func.count(EnvironmentalFeature.id).label("cell_count"),
    ).where(
        EnvironmentalFeature.hvi_score.isnot(None),
    )

    if ward_id:
        from app.models.spatial_grid import SpatialGrid
        base = (
            base.join(SpatialGrid, SpatialGrid.id == EnvironmentalFeature.grid_id)
            .where(SpatialGrid.ward_id == ward_id)
        )

    base = base.group_by(EnvironmentalFeature.year).order_by(EnvironmentalFeature.year)

    result = await db.execute(base)
    rows = result.all()

    trend = []
    for row in rows:
        # Get tier distribution for this year
        tier_stmt = select(
            EnvironmentalFeature.hvi_tier,
            func.count(EnvironmentalFeature.id).label("count"),
        ).where(
            EnvironmentalFeature.year == row.year,
            EnvironmentalFeature.hvi_tier.isnot(None),
        )

        if ward_id:
            from app.models.spatial_grid import SpatialGrid
            tier_stmt = (
                tier_stmt.join(
                    SpatialGrid, SpatialGrid.id == EnvironmentalFeature.grid_id
                ).where(SpatialGrid.ward_id == ward_id)
            )

        tier_stmt = tier_stmt.group_by(EnvironmentalFeature.hvi_tier)
        tier_result = await db.execute(tier_stmt)
        tiers = {t.hvi_tier: t.count for t in tier_result.all()}

        trend.append({
            "year": row.year,
            "avg_hvi": round(float(row.avg_hvi), 2) if row.avg_hvi else None,
            "max_hvi": round(float(row.max_hvi), 2) if row.max_hvi else None,
            "min_hvi": round(float(row.min_hvi), 2) if row.min_hvi else None,
            "cell_count": row.cell_count,
            "tier_distribution": tiers,
        })

    return {"ward_id": ward_id, "trend": trend}
