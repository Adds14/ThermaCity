"""HVI (Heat Vulnerability Index) Pydantic v2 schemas for ThermaCity."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Canonical tier labels
HVITier = Literal["Heat-Safe", "Caution", "Stressed", "Emergency"]


# ---------------------------------------------------------------------------
# City-wide HVI summary for a given year
# ---------------------------------------------------------------------------

class HVISummary(BaseModel):
    """Aggregate HVI statistics for the entire city in a single year."""

    model_config = ConfigDict(from_attributes=True)

    year: int = Field(..., ge=2020, le=2030, description="Reference year.", examples=[2024])
    total_cells: int = Field(..., ge=0, description="Number of grid cells included.", examples=[1200])
    avg_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Mean HVI score across all cells.",
        examples=[47.3],
    )
    max_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Maximum HVI score observed.",
        examples=[94.1],
    )
    min_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Minimum HVI score observed.",
        examples=[8.2],
    )
    tier_distribution: dict[HVITier, int] = Field(
        ...,
        description="Count of cells in each HVI tier.",
        examples=[{"Heat-Safe": 300, "Caution": 450, "Stressed": 350, "Emergency": 100}],
    )


# ---------------------------------------------------------------------------
# Ward-level HVI summary
# ---------------------------------------------------------------------------

class HVIWardSummary(BaseModel):
    """HVI summary aggregated at the ward level."""

    model_config = ConfigDict(from_attributes=True)

    ward_id: int = Field(..., description="Ward primary-key.", examples=[7])
    ward_name: str = Field(..., description="Human-readable ward name.", examples=["Kothrud"])
    avg_hvi: float = Field(
        ...,
        ge=0,
        le=100,
        description="Mean HVI across cells in this ward.",
        examples=[52.6],
    )
    max_hvi: float = Field(
        ...,
        ge=0,
        le=100,
        description="Maximum HVI in this ward.",
        examples=[88.4],
    )
    cell_count: int = Field(..., ge=0, description="Number of grid cells in the ward.", examples=[85])
    dominant_tier: HVITier = Field(
        ...,
        description="Tier with the highest cell count in this ward.",
        examples=["Stressed"],
    )


# ---------------------------------------------------------------------------
# Single temporal data-point (for time-series charts)
# ---------------------------------------------------------------------------

class HVITemporalPoint(BaseModel):
    """One data-point in an HVI time-series."""

    model_config = ConfigDict(from_attributes=True)

    year: int = Field(..., ge=2020, le=2030, description="Reference year.", examples=[2024])
    avg_hvi: float = Field(
        ...,
        ge=0,
        le=100,
        description="City-wide (or ward-level) average HVI.",
        examples=[49.7],
    )
    max_hvi: float = Field(
        ...,
        ge=0,
        le=100,
        description="Maximum HVI for this year.",
        examples=[93.2],
    )
    tier_distribution: dict[HVITier, int] = Field(
        ...,
        description="Cell counts per tier for this year.",
        examples=[{"Heat-Safe": 310, "Caution": 440, "Stressed": 340, "Emergency": 110}],
    )
