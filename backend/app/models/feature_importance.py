"""
ThermaCity — Feature Importance Model

Stores Random Forest feature importance scores per model version.
Used by the explainability endpoint to show which environmental
variables drive heat vulnerability in each ward.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FeatureImportance(Base):
    """Feature importance score for a single feature in a model version."""

    __tablename__ = "feature_importance"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    model_version: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="e.g. 'v1', 'v2'"
    )
    feature_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="e.g. 'ndvi', 'ndbi', 'tree_canopy_frac'"
    )
    importance_score: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Gini importance (0.0–1.0)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Constraints ───────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "model_version", "feature_name",
            name="uq_model_feature",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<FeatureImportance(model={self.model_version!r}, "
            f"feature={self.feature_name!r}, score={self.importance_score})>"
        )
