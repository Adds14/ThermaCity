"""
ThermaCity — SQLAlchemy Declarative Base

All ORM models inherit from this Base class.
GeoAlchemy2 is imported here to ensure PostGIS types are
registered with SQLAlchemy's type system.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ThermaCity ORM models."""
    pass
