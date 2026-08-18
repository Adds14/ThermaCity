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
    )
    ward_result = await db.execute(ward_stmt)
    ward_id = ward_result.scalar_one_or_none()
    
    if ward_id:
        report.ward_id = ward_id

    # Perform ST_Contains to assign grid_id
    grid_stmt = select(SpatialGrid.id).where(
        SpatialGrid.geom.ST_Contains(point_geom)
    )
    grid_result = await db.execute(grid_stmt)
    grid_id = grid_result.scalar_one_or_none()

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
def download_pdf_report(
    year: int = Query(2024, ge=2021, le=2026, description="Data year for the report"),
):
    """
    Generate and download a PDF heat vulnerability assessment report.

    Loads the demo grid data for the requested year, extracts the summary
    statistics and top-10 highest-risk cells, then streams back a
    publication-ready PDF document.
    """
    from app.routers.demo import _load_year

    try:
        data = _load_year(year)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to load data for PDF report (year=%d)", year)
        raise HTTPException(
            status_code=500,
            detail=f"Could not load data for year {year}: {exc}",
        )

    summary = data["summary"]

    # Extract top 10 cells by HVI score from the cached GeoJSON
    features = data["geojson"].get("features", [])
    sorted_cells = sorted(
        features,
        key=lambda f: f.get("properties", {}).get("hvi_score", 0),
        reverse=True,
    )
    top_cells = [f["properties"] for f in sorted_cells[:10]]

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
