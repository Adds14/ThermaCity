"""What-if scenario Pydantic v2 schemas for ThermaCity."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Re-use the canonical tier type
HVITier = Literal["Heat-Safe", "Caution", "Stressed", "Emergency"]


# ---------------------------------------------------------------------------
# Request (POST body)
# ---------------------------------------------------------------------------

class ScenarioRequest(BaseModel):
    """Parameters for a what-if urban-heat scenario simulation."""

    model_config = ConfigDict(from_attributes=True)

    cell_ids: list[int] = Field(
        ...,
        min_length=1,
        description="List of grid-cell primary keys to simulate.",
        examples=[[10, 11, 12]],
    )
    ndvi_delta: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Change in NDVI to apply (e.g. +0.1 for more vegetation).",
        examples=[0.05],
    )
    ndbi_delta: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Change in NDBI to apply.",
        examples=[-0.03],
    )
    ndwi_delta: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Change in NDWI to apply.",
        examples=[0.02],
    )
    tree_canopy_delta: float = Field(
        default=0.0,
        ge=-100.0,
        le=100.0,
        description="Change in tree-canopy cover percentage points.",
        examples=[5.0],
    )
    year: int = Field(
        ...,
        ge=2020,
        le=2030,
        description="Target year for the simulation baseline.",
        examples=[2025],
    )

    @field_validator("cell_ids")
    @classmethod
    def _cell_ids_unique(cls, v: list[int]) -> list[int]:
        if len(v) != len(set(v)):
            raise ValueError("cell_ids must contain unique values.")
        return v


# ---------------------------------------------------------------------------
# Result (one per cell)
# ---------------------------------------------------------------------------

class ScenarioResult(BaseModel):
    """Simulation output for a single grid cell."""

    model_config = ConfigDict(from_attributes=True)

    cell_id: int = Field(..., description="Grid-cell primary key.", examples=[10])
    cell_code: str = Field(
        ...,
        description="Unique cell code.",
        examples=["PUNE_G_1234"],
    )

    # LST
    original_lst: float = Field(
        ...,
        description="Baseline Land Surface Temperature (°C).",
        examples=[38.2],
    )
    simulated_lst: float = Field(
        ...,
        description="Simulated LST after applying deltas (°C).",
        examples=[36.5],
    )
    lst_delta: float = Field(
        ...,
        description="Change in LST (simulated − original).",
        examples=[-1.7],
    )

    # HVI
    original_hvi: float = Field(
        ...,
        ge=0,
        le=100,
        description="Baseline HVI score.",
        examples=[62.4],
    )
    simulated_hvi: float = Field(
        ...,
        ge=0,
        le=100,
        description="Simulated HVI score.",
        examples=[51.8],
    )
    hvi_delta: float = Field(
        ...,
        description="Change in HVI (simulated − original).",
        examples=[-10.6],
    )

    # Tiers
    original_tier: HVITier = Field(
        ...,
        description="HVI tier before simulation.",
        examples=["Stressed"],
    )
    simulated_tier: HVITier = Field(
        ...,
        description="HVI tier after simulation.",
        examples=["Caution"],
    )
