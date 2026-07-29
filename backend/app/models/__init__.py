"""
ThermaCity — ORM Model Registry

Import all models here so that:
  1. Alembic's `Base.metadata` sees every table for autogeneration.
  2. Relationship back_populates resolve correctly.
  3. Other modules can do: `from app.models import SpatialGrid, ...`
"""

from app.models.base import Base
from app.models.ward_boundary import WardBoundary
from app.models.spatial_grid import SpatialGrid
from app.models.environmental_features import EnvironmentalFeature
from app.models.community_report import CommunityReport, REPORT_CATEGORIES
from app.models.feature_importance import FeatureImportance

__all__ = [
    "Base",
    "WardBoundary",
    "SpatialGrid",
    "EnvironmentalFeature",
    "CommunityReport",
    "FeatureImportance",
    "REPORT_CATEGORIES",
]
