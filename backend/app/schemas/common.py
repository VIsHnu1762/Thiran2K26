"""
BillAgent Pro - Common Schemas
===============================
Shared schema definitions used across the application.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field
from uuid import UUID


# =============================================================================
# Generic Types
# =============================================================================
T = TypeVar("T")


# =============================================================================
# Task Status (for async processing)
# =============================================================================
class TaskStatus(str, Enum):
    """Status of an async task."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskResponse(BaseModel):
    """Response for async task submission."""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    message: str = Field(..., description="Status message")
    progress: Optional[float] = Field(None, ge=0, le=1, description="Progress (0.0 to 1.0)")
    estimated_time_seconds: Optional[int] = Field(None, description="Estimated time to completion")
    bill_id: Optional[UUID] = Field(None, description="Bill ID (when completed)")
    error: Optional[str] = Field(None, description="Error message (when failed)")
    
    model_config = {"from_attributes": True}


# =============================================================================
# Validation
# =============================================================================
class ValidationError(BaseModel):
    """A single validation error."""
    field: str = Field(..., description="Field name that has the error")
    message: str = Field(..., description="Human-readable error message")
    severity: str = Field(default="error", description="Error severity: 'error' or 'warning'")
    expected_value: Optional[Any] = Field(None, description="Expected value")
    actual_value: Optional[Any] = Field(None, description="Actual value found")
    
    model_config = {"from_attributes": True}


class ValidationResult(BaseModel):
    """Result of validation by the Auditor Agent."""
    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[ValidationError] = Field(default_factory=list, description="List of errors")
    warnings: List[ValidationError] = Field(default_factory=list, description="List of warnings")
    suggested_status: str = Field(..., description="Suggested bill status based on validation")
    
    model_config = {"from_attributes": True}


# =============================================================================
# Pagination
# =============================================================================
class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")
    
    model_config = {"from_attributes": True}


# =============================================================================
# Health Check
# =============================================================================
class HealthCheck(BaseModel):
    """Health check response."""
    status: str = Field(default="healthy", description="Service status")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment name")
    database: str = Field(default="connected", description="Database status")
    redis: str = Field(default="connected", description="Redis status")
    celery: Optional[str] = Field(default=None, description="Celery worker status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp")
    
    model_config = {"from_attributes": True}


# =============================================================================
# Error Response
# =============================================================================
class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    model_config = {"from_attributes": True}


# =============================================================================
# Bounding Box
# =============================================================================
class BoundingBox(BaseModel):
    """Bounding box coordinates for OCR regions."""
    x: float = Field(..., ge=0, description="X coordinate")
    y: float = Field(..., ge=0, description="Y coordinate")
    width: float = Field(..., ge=0, description="Width")
    height: float = Field(..., ge=0, description="Height")
    
    model_config = {"from_attributes": True}


# =============================================================================
# Dashboard Stats
# =============================================================================
class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_bills: int = Field(default=0, description="Total bills processed")
    pending_review: int = Field(default=0, description="Bills awaiting review")
    approved_today: int = Field(default=0, description="Bills approved today")
    failed_today: int = Field(default=0, description="Bills failed today")
    total_amount: float = Field(default=0.0, description="Total amount processed")
    average_confidence: float = Field(default=0.0, description="Average OCR confidence")
    average_processing_time_ms: int = Field(default=0, description="Average processing time")
    top_vendors: List[Dict[str, Any]] = Field(default_factory=list, description="Top vendors by volume")
    
    model_config = {"from_attributes": True}
