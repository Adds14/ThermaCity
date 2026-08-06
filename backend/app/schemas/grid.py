"""Grid-cell Pydantic v2 schemas for ThermaCity."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class GridCellBase(BaseModel):
    """Minimal representation shared by every grid-cell schema."""

    model_config = ConfigDict(from_attributes=True)

    cell_code: str = Field(
        ...,
        min_length=1,
        description="Unique alphanumeric code identifying the grid cell.",
        examples=["PUNE_G_1234"],
    )
    ward_id: Optional[int] = Field(
        default=None,
        description="Foreign-key to the ward this cell falls in (nullable for border cells).",
        examples=[7],
    )


# ---------------------------------------------------------------------------
# Response (list / map endpoints)
# ---------------------------------------------------------------------------

class GridCellResponse(GridCellBase):
    """Grid cell returned by list / map-tile endpoints."""

    id: int = Field(..., description="Primary-key identifier.", examples=[42])
    centroid_lat: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude of the cell centroid (WGS-84).",
        examples=[18.5204],
    )
    centroid_lng: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude of the cell centroid (WGS-84).",
        examples=[73.8567],
    )


# ---------------------------------------------------------------------------
# Historical feature point (embedded in detail)
# ---------------------------------------------------------------------------

class HistoricalFeature(BaseModel):
    """A single year's remote-sensing features for a grid cell."""

    model_config = ConfigDict(from_attributes=True)

    year: int = Field(..., ge=2020, le=2030, description="Observation year.", examples=[2024])
    ndvi: Optional[float] = Field(default=None, description="Normalised Difference Vegetation Index.")
    ndbi: Optional[float] = Field(default=None, description="Normalised Difference Built-up Index.")
    ndwi: Optional[float] = Field(default=None, description="Normalised Difference Water Index.")
    lst: Optional[float] = Field(default=None, description="Land Surface Temperature (°C).")
    tree_canopy: Optional[float] = Field(default=None, ge=0, le=100, description="Tree-canopy cover (%).")
    hvi_score: Optional[float] = Field(default=None, ge=0, le=100, description="Heat Vulnerability Index score.")
    hvi_tier: Optional[str] = Field(default=None, description="HVI tier label.", examples=["Caution"])


# ---------------------------------------------------------------------------
# Detail (single-cell deep-dive)
# ---------------------------------------------------------------------------

class GridCellDetail(GridCellResponse):
    """Full detail for a single grid cell, including yearly history."""

    historical_features: list[HistoricalFeature] = Field(
        default_factory=list,
        description="Time-series of remote-sensing features & HVI scores.",
    )


# ---------------------------------------------------------------------------
# GeoJSON Feature wrapper
# ---------------------------------------------------------------------------

class GridCellGeoJSON(BaseModel):
    """GeoJSON Feature representation of a grid cell."""

    model_config = ConfigDict(from_attributes=True)

    type: str = Field(default="Feature", description="GeoJSON object type.")
    geometry: dict[str, Any] = Field(
        ...,
        description="GeoJSON geometry object (typically Polygon).",
        examples=[{
            "type": "Polygon",
            "coordinates": [[[73.85, 18.52], [73.86, 18.52], [73.86, 18.53], [73.85, 18.53], [73.85, 18.52]]],
        }],
    )
    properties: dict[str, Any] = Field(
        ...,
        description="Arbitrary properties attached to the feature (cell_code, hvi_score, tier, etc.).",
    )
