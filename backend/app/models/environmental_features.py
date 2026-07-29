"""
ThermaCity — Environmental Features Model

Per-cell, per-year environmental features extracted from GEE,
plus ML predictions and computed HVI.

One row per grid cell per year (2021–2026).
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EnvironmentalFeature(Base):
    """Environmental features + HVI for a single grid cell in a single year."""

    __tablename__ = "environmental_features"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Foreign Key ───────────────────────────────────────────
    grid_id: Mapped[int] = mapped_column(
        ForeignKey("spatial_grid.id", ondelete="CASCADE"),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # ── Satellite-Derived Features (GEE Pipeline Output) ─────
    lst_observed: Mapped[float | None] = mapped_column(
        Float, comment="Landsat 8/9 LST (°C), hot-season median"
    )
    ndvi: Mapped[float | None] = mapped_column(
        Float, comment="Sentinel-2 NDVI (-1 to 1)"
    )
    ndbi: Mapped[float | None] = mapped_column(
        Float, comment="Sentinel-2 NDBI (-1 to 1)"
    )
    ndwi: Mapped[float | None] = mapped_column(
        Float, comment="Sentinel-2 NDWI (-1 to 1)"
    )
    tree_canopy_frac: Mapped[float | None] = mapped_column(
        Float, comment="ESA WorldCover tree cover fraction (0.0–1.0)"
    )

    # ── Climate Reanalysis (ERA5-Land) ────────────────────────
    humidity: Mapped[float | None] = mapped_column(
        Float, comment="Relative humidity (%)"
    )
    wind_speed: Mapped[float | None] = mapped_column(
        Float, comment="Wind speed (m/s)"
    )

    # ── Demographics (WorldPop) ───────────────────────────────
    population_density: Mapped[float | None] = mapped_column(
        Float, comment="Persons per km²"
    )

    # ── ML Model Output ──────────────────────────────────────
    lst_predicted: Mapped[float | None] = mapped_column(
        Float, comment="Random Forest LST prediction (°C)"
    )

    # ── Computed HVI ──────────────────────────────────────────
    hvi_score: Mapped[float | None] = mapped_column(
        Float, comment="Heat Vulnerability Index (0–100)"
    )
    hvi_tier: Mapped[str | None] = mapped_column(
        String(10), comment="Low / Moderate / High / Severe"
    )

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ─────────────────────────────────────────
    grid_cell = relationship("SpatialGrid", back_populates="features")

    # ── Constraints & Indexes ─────────────────────────────────
    __table_args__ = (
        UniqueConstraint("grid_id", "year", name="uq_grid_year"),
        CheckConstraint("year BETWEEN 2020 AND 2030", name="ck_year_range"),
        CheckConstraint(
            "tree_canopy_frac IS NULL OR (tree_canopy_frac BETWEEN 0.0 AND 1.0)",
            name="ck_canopy_range",
        ),
        CheckConstraint(
            "hvi_score IS NULL OR (hvi_score BETWEEN 0 AND 100)",
            name="ck_hvi_range",
        ),
        CheckConstraint(
            "hvi_tier IS NULL OR hvi_tier IN ('Low', 'Moderate', 'High', 'Severe')",
            name="ck_hvi_tier",
        ),
        Index("idx_envfeat_grid_year", "grid_id", "year"),
        Index("idx_envfeat_year", "year"),
        Index("idx_envfeat_hvi", "hvi_score"),
        Index("idx_envfeat_tier", "hvi_tier"),
    )

    def __repr__(self) -> str:
        return (
            f"<EnvironmentalFeature(grid_id={self.grid_id}, "
            f"year={self.year}, hvi={self.hvi_score})>"
        )
