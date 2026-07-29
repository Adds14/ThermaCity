"""
ThermaCity — Ward Boundaries Model

Pune Municipal Corporation administrative ward polygons.
Source: DataMeet GitHub — Municipal_Spatial_Data.
"""

from geoalchemy2 import Geometry
from sqlalchemy import Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class WardBoundary(Base):
    """PMC administrative ward polygon."""

    __tablename__ = "ward_boundaries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ward_name: Mapped[str] = mapped_column(String(100), nullable=False)
    ward_code: Mapped[str | None] = mapped_column(String(20), unique=True)
    zone_name: Mapped[str | None] = mapped_column(String(100))
    area_sq_km: Mapped[float | None] = mapped_column(Float)

    # PostGIS geometry — MultiPolygon, EPSG:4326
    geom = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────
    grid_cells = relationship("SpatialGrid", back_populates="ward")
    community_reports = relationship("CommunityReport", back_populates="ward")

    # ── Spatial Index ─────────────────────────────────────────
    __table_args__ = (
        Index("idx_ward_geom", geom, postgresql_using="gist"),
    )

    def __repr__(self) -> str:
        return f"<WardBoundary(id={self.id}, name={self.ward_name!r})>"
