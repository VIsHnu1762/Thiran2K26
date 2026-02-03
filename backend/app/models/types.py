"""
Custom SQLAlchemy types for cross-database compatibility.
"""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB as PostgresJSONB
from sqlalchemy.types import TypeDecorator

from ..config import settings


def get_json_type():
    """
    Return appropriate JSON type based on database.
    Uses JSONB for PostgreSQL, JSON for SQLite.
    """
    if settings.database_type == "postgresql":
        return PostgresJSONB
    return JSON
