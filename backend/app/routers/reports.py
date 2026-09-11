"""
ThermaCity — Community Reports Router

Endpoints for submitting and retrieving crowdsourced heat vulnerability reports,
and downloading PDF heat vulnerability assessment reports.
"""

import io
import logging

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.community_report import CommunityReport
from app.models.spatial_grid import SpatialGrid
from app.models.ward_boundary import WardBoundary
from app.schemas.report import ReportCreate, ReportResponse
from app.services.geojson_builder import build_feature_collection
from app.services.report_generator import generate_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Community Reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def submit_report(
    payload: ReportCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a new community report.

    Expects a latitude/longitude point. The backend automatically performs a
    spatial query to assign this point to the correct 100x100m grid cell
    and municipal ward using PostGIS `ST_Contains`.
    """
    from geoalchemy2.elements import WKTElement

    # Create a Point geometry from lat/lng
    point_wkt = f"SRID=4326;POINT({payload.longitude} {payload.latitude})"
    point_geom = WKTElement(point_wkt, srid=4326)

    report = CommunityReport(
        category=payload.category,
        description=payload.description,
        severity=payload.severity,
        heat_impact_rating=payload.heat_impact_rating,
        shade_rating=payload.shade_rating,
        water_rating=payload.water_rating,
        reporter_name=payload.reporter_name,
        geom=point_geom,
    )

    db.add(report)
    await db.flush()  # To assign spatial ID and let triggers run if any, or we query below

    # Perform ST_Contains to assign ward_id
    ward_stmt = select(WardBoundary.id).where(
        WardBoundary.geom.ST_Contains(point_geom)
    ).limit(1)
    ward_result = await db.execute(ward_stmt)
    ward_id = ward_result.scalars().first()
    
    if ward_id:
        report.ward_id = ward_id

    # Perform ST_Contains to assign grid_id
    grid_stmt = select(SpatialGrid.id).where(
        SpatialGrid.geom.ST_Contains(point_geom)
    ).limit(1)
    grid_result = await db.execute(grid_stmt)
    grid_id = grid_result.scalars().first()

    if grid_id:
        report.grid_id = grid_id

    await db.commit()
    await db.refresh(report)

    # Fetch with relationships for response
    stmt = (
        select(CommunityReport)
        .where(CommunityReport.id == report.id)
        .options(
            selectinload(CommunityReport.ward),
            selectinload(CommunityReport.grid_cell)
        )
    )
    result = await db.execute(stmt)
    report_loaded = result.scalar_one()

    return _to_response(report_loaded)


@router.get("")
async def list_reports(
    category: str | None = Query(None, description="Filter by report category"),
    is_verified: bool | None = Query(None, description="Filter by verified status"),
    ward_id: int | None = Query(None, description="Filter by ward ID"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """
    List community reports as a GeoJSON FeatureCollection.
    """
    stmt = select(CommunityReport).options(
        selectinload(CommunityReport.ward),
        selectinload(CommunityReport.grid_cell)
    ).order_by(desc(CommunityReport.created_at))

    if category:
        stmt = stmt.where(CommunityReport.category == category)
    if is_verified is not None:
        stmt = stmt.where(CommunityReport.is_verified == is_verified)
    if ward_id:
        stmt = stmt.where(CommunityReport.ward_id == ward_id)

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    features = []
    for row in rows:
        props = {
            "id": row.id,
            "category": row.category,
            "description": row.description,
            "severity": row.severity,
            "heat_impact_rating": row.heat_impact_rating,
            "shade_rating": row.shade_rating,
            "water_rating": row.water_rating,
            "is_verified": row.is_verified,
            "reporter_name": row.reporter_name,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "ward_name": row.ward.ward_name if row.ward else None,
            "cell_code": row.grid_cell.cell_code if row.grid_cell else None,
        }
        
        # Parse point
        try:
            from geoalchemy2.shape import to_shape
            from shapely.geometry import mapping
            geom_dict = mapping(to_shape(row.geom))
        except Exception:
            geom_dict = None

        features.append({
            "type": "Feature",
            "geometry": geom_dict,
            "properties": props
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


@router.get("/download")
async def download_pdf_report(
    year: int = Query(2024, ge=2021, le=2026, description="Data year for the report"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate and download a PDF heat vulnerability assessment report.
    """
    # 1. Fetch summary statistics
    stmt = select(
        func.count(EnvironmentalFeature.id).label("total_cells"),
        func.avg(EnvironmentalFeature.hvi_score).label("avg_hvi"),
        func.max(EnvironmentalFeature.hvi_score).label("max_hvi"),
        func.min(EnvironmentalFeature.hvi_score).label("min_hvi"),
        func.avg(EnvironmentalFeature.lst_predicted).label("avg_lst")
    ).where(EnvironmentalFeature.year == year)
    
    result = await db.execute(stmt)
    row = result.one()
    
    tier_stmt = select(
        EnvironmentalFeature.hvi_tier,
        func.count(EnvironmentalFeature.id).label("count"),
    ).where(EnvironmentalFeature.year == year).group_by(EnvironmentalFeature.hvi_tier)
    tier_result = await db.execute(tier_stmt)
    tier_distribution = {t.hvi_tier: t.count for t in tier_result.all()}

    summary = {
        "year": year,
        "total_cells": row.total_cells,
        "avg_hvi": round(float(row.avg_hvi or 0), 2),
        "max_hvi": round(float(row.max_hvi or 0), 2),
        "min_hvi": round(float(row.min_hvi or 0), 2),
        "avg_lst": round(float(row.avg_lst or 0), 2),
        "tier_distribution": tier_distribution,
        "emergency_cells": tier_distribution.get("Emergency", 0),
        "high_risk_cells": tier_distribution.get("Stressed", 0) + tier_distribution.get("Emergency", 0),
    }

    # 2. Fetch top 10 hottest cells
    hotspots_stmt = select(EnvironmentalFeature).where(
        EnvironmentalFeature.year == year
    ).order_by(EnvironmentalFeature.hvi_score.desc()).limit(10)
    hotspots_result = await db.execute(hotspots_stmt)
    
    top_cells = []
    for f in hotspots_result.scalars().all():
        top_cells.append({
            "lst_predicted": f.lst_predicted,
            "hvi_score": f.hvi_score,
            "hvi_tier": f.hvi_tier
        })

    pdf_bytes = generate_report(summary=summary, top_cells=top_cells, year=year)

    filename = f"ThermaCity_Report_{year}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )

from pydantic import BaseModel

class CellReportRequest(BaseModel):
    cell_id: int
    year: int
    baseline_lst: float
    baseline_ndvi: float
    baseline_ndbi: float
    baseline_hvi_score: float
    baseline_hvi_tier: str
    simulated_lst: float | None = None
    simulated_hvi_tier: str | None = None
    lst_delta: float | None = None
    applied_canopy_delta: float | None = None
    applied_ndbi_delta: float | None = None

from fastapi.responses import Response

@router.post("/cell")
def generate_cell_pdf(req: CellReportRequest):
    """Generate a PDF report for a specific grid cell."""
    from app.services.report_generator import generate_cell_report
    pdf_bytes = generate_cell_report(req.model_dump())
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=thermacity_block_{req.cell_id}.pdf"
        }
    )


@router.patch("/{report_id}/verify", response_model=ReportResponse)
async def verify_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a community report (Admin only).
    """
    stmt = (
        select(CommunityReport)
        .where(CommunityReport.id == report_id)
        .options(
            selectinload(CommunityReport.ward),
            selectinload(CommunityReport.grid_cell)
        )
    )
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.is_verified = True
    await db.commit()
    await db.refresh(report)

    return _to_response(report)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a community report (Admin only).
    """
    stmt = select(CommunityReport).where(CommunityReport.id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    await db.delete(report)
    await db.commit()



def _to_response(report: CommunityReport) -> ReportResponse:
    # Helper to extract lat/lng and map to Pydantic schema
    try:
        from geoalchemy2.shape import to_shape
        pt = to_shape(report.geom)
        lon, lat = pt.x, pt.y
    except Exception:
        lon, lat = 0.0, 0.0

    return ReportResponse(
        id=report.id,
        category=report.category,
        description=report.description,
        severity=report.severity,
        heat_impact_rating=report.heat_impact_rating,
        shade_rating=report.shade_rating,
        water_rating=report.water_rating,
        is_verified=report.is_verified,
        reporter_name=report.reporter_name,
        created_at=report.created_at,
        latitude=lat,
        longitude=lon,
        ward_name=report.ward.ward_name if report.ward else None,
        cell_code=report.grid_cell.cell_code if report.grid_cell else None,
    )
