"""
ThermaCity — Community Report Model

Geo-tagged citizen observations of heat-related infrastructure gaps.
Location is auto-assigned to the containing grid cell and ward via
a PostGIS trigger (see db/init.sql).
"""

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


# Valid report categories — matches the CHECK constraint in init.sql
REPORT_CATEGORIES = [
    "extreme_heat",
    "lack_of_shade",
    "hot_pavement",
    "bus_stop_no_shade",
    "water_fountain_unavailable",
    "cooling_shelter_closed",
]


class CommunityReport(Base):
    """Citizen-submitted geo-tagged heat vulnerability report."""

    __tablename__ = "community_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Report Content ────────────────────────────────────────
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reporter_name: Mapped[str | None] = mapped_column(String(100))
    photo_url: Mapped[str | None] = mapped_column(String(500))

    # ── Spatial References (auto-assigned by DB trigger) ──────
    grid_id: Mapped[int | None] = mapped_column(
        ForeignKey("spatial_grid.id", ondelete="SET NULL"),
    )
    ward_id: Mapped[int | None] = mapped_column(
        ForeignKey("ward_boundaries.id", ondelete="SET NULL"),
    )

    # ── Moderation ────────────────────────────────────────────
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── PostGIS Geometry ──────────────────────────────────────
    geom = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────
    grid_cell = relationship("SpatialGrid", back_populates="community_reports")
    ward = relationship("WardBoundary", back_populates="community_reports")

    # ── Constraints & Indexes ─────────────────────────────────
    __table_args__ = (
        CheckConstraint(
            f"category IN ({', '.join(repr(c) for c in REPORT_CATEGORIES)})",
            name="ck_report_category",
        ),
        CheckConstraint(
            "severity BETWEEN 1 AND 5",
            name="ck_report_severity",
        ),
        Index("idx_reports_geom", geom, postgresql_using="gist"),
        Index("idx_reports_category", "category"),
        Index("idx_reports_ward", "ward_id"),
        Index("idx_reports_created", "created_at"),
        Index("idx_reports_verified", "is_verified"),
    )

    def __repr__(self) -> str:
        return (
            f"<CommunityReport(id={self.id}, category={self.category!r}, "
            f"severity={self.severity})>"
        )
