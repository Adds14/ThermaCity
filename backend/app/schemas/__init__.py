"""ThermaCity — Pydantic v2 schemas package.

Re-exports every public schema so callers can write::

    from app.schemas import GridCellResponse, ReportCreate, ScenarioRequest
"""

from .grid import (
    GridCellBase,
    GridCellDetail,
    GridCellGeoJSON,
    GridCellResponse,
    HistoricalFeature,
)
from .hvi import (
    HVISummary,
    HVITemporalPoint,
    HVIWardSummary,
)
from .report import (
    ReportCreate,
    ReportFilter,
    ReportResponse,
)
from .scenario import (
    ScenarioRequest,
    ScenarioResult,
)

__all__ = [
    # grid
    "GridCellBase",
    "GridCellResponse",
    "GridCellDetail",
    "GridCellGeoJSON",
    "HistoricalFeature",
    # hvi
    "HVISummary",
    "HVIWardSummary",
    "HVITemporalPoint",
    # report
    "ReportCreate",
    "ReportResponse",
    "ReportFilter",
    # scenario
    "ScenarioRequest",
    "ScenarioResult",
]
