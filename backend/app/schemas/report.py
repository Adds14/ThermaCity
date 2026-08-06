"""Community-report Pydantic v2 schemas for ThermaCity."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Canonical report categories
ReportCategory = Literal[
    "extreme_heat",
    "lack_of_shade",
    "hot_pavement",
    "bus_stop_no_shade",
    "water_fountain_unavailable",
    "cooling_shelter_closed",
]


# ---------------------------------------------------------------------------
# Create (POST body)
# ---------------------------------------------------------------------------

class ReportCreate(BaseModel):
    """Payload submitted by a community member to file a heat-related report."""

    model_config = ConfigDict(from_attributes=True)

    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude where the issue was observed (WGS-84).",
        examples=[18.5204],
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude where the issue was observed (WGS-84).",
        examples=[73.8567],
    )
    category: ReportCategory = Field(
        ...,
        description="Predefined category of the report.",
        examples=["extreme_heat"],
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Free-text description of the issue.",
        examples=["No shade near bus stop on Karve Road."],
    )
    severity: int = Field(
        ...,
        ge=1,
        le=5,
        description="Perceived severity (1 = minor, 5 = critical).",
        examples=[4],
    )
    reporter_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional name of the person filing the report.",
        examples=["Anjali S."],
    )


# ---------------------------------------------------------------------------
# Response (GET single / list items)
# ---------------------------------------------------------------------------

class ReportResponse(BaseModel):
    """A community report as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Primary-key identifier.", examples=[101])
    category: ReportCategory = Field(
        ...,
        description="Report category.",
        examples=["lack_of_shade"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Free-text description.",
    )
    severity: int = Field(
        ...,
        ge=1,
        le=5,
        description="Severity rating.",
        examples=[3],
    )
    reporter_name: Optional[str] = Field(
        default=None,
        description="Name of the reporter (if provided).",
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the report was filed.",
        examples=["2025-05-15T10:30:00Z"],
    )
    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude of the reported issue.",
        examples=[18.5204],
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude of the reported issue.",
        examples=[73.8567],
    )
    ward_name: Optional[str] = Field(
        default=None,
        description="Ward the report was geo-matched to.",
        examples=["Kothrud"],
    )
    cell_code: Optional[str] = Field(
        default=None,
        description="Grid cell the report falls within.",
        examples=["PUNE_G_1234"],
    )


# ---------------------------------------------------------------------------
# Filter / pagination (query params)
# ---------------------------------------------------------------------------

class ReportFilter(BaseModel):
    """Query-string parameters for listing / filtering community reports."""

    model_config = ConfigDict(from_attributes=True)

    category: Optional[ReportCategory] = Field(
        default=None,
        description="Filter by report category.",
    )
    ward_id: Optional[int] = Field(
        default=None,
        description="Filter by ward primary-key.",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed).",
        examples=[1],
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of results per page.",
        examples=[20],
    )
