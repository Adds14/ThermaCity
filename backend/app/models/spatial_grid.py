"""
ThermaCity — Spatial Grid Model

100×100 m analysis grid cells covering Pune.
Each cell is the atomic spatial unit for feature extraction and HVI computation.
"""

from geoalchemy2 import Geometry
from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SpatialGrid(Base):
    """100×100 m grid cell polygon."""

    __tablename__ = "spatial_grid"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Unique cell identifier, e.g. "PUNE_R0042_C0117"
    cell_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )

    # Foreign key to ward (nullable — cells on boundary may be unassigned)
    ward_id: Mapped[int | None] = mapped_column(
        ForeignKey("ward_boundaries.id", ondelete="SET NULL"),
        index=True,
    )

    # Precomputed centroid for fast non-spatial lookups
    centroid_lat: Mapped[float | None] = mapped_column(Float)
    centroid_lng: Mapped[float | None] = mapped_column(Float)

    # PostGIS geometry — Polygon, EPSG:4326
    geom = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────
    ward = relationship("WardBoundary", back_populates="grid_cells")
    features = relationship(
        "EnvironmentalFeature",
        back_populates="grid_cell",
        cascade="all, delete-orphan",
    )
    community_reports = relationship(
        "CommunityReport",
        back_populates="grid_cell",
    )

    # ── Indexes ───────────────────────────────────────────────
    __table_args__ = (
        Index("idx_grid_geom", geom, postgresql_using="gist"),
    )

    def __repr__(self) -> str:
        return f"<SpatialGrid(id={self.id}, cell_code={self.cell_code!r})>"
