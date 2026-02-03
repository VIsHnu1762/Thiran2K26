"""
BillAgent Pro - Bill Schemas
=============================
Pydantic schemas for Bill operations.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from .vendor_schema import VendorSummary, VendorRead
from .line_item_schema import LineItemCreate, LineItemRead, LineItemUpdate
from .common import ValidationError, BoundingBox, TaskStatus


class BillStatus(str, Enum):
    """Bill processing status."""
    PROCESSING = "PROCESSING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    POSTED = "POSTED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class BillBase(BaseModel):
    """Base bill schema with common fields."""
    invoice_number: Optional[str] = Field(None, max_length=100, description="Invoice number")
    invoice_date: Optional[date] = Field(None, description="Invoice date")
    due_date: Optional[date] = Field(None, description="Payment due date")
    subtotal: Optional[Decimal] = Field(None, ge=0, description="Subtotal before tax")
    tax_amount: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, description="Tax amount")
    total_amount: Optional[Decimal] = Field(None, ge=0, description="Grand total")
    currency: str = Field(default="INR", max_length=3, description="Currency code")
    notes: Optional[str] = Field(None, description="User notes")


class BillCreate(BillBase):
    """Schema for creating a bill."""
    vendor_id: Optional[UUID] = Field(None, description="Vendor ID")
    vendor_name: Optional[str] = Field(None, description="Vendor name (for auto-creation)")
    image_url: str = Field(..., description="Path to bill image")
    line_items: List[LineItemCreate] = Field(default_factory=list, description="Line items")
    
    @field_validator("invoice_date", mode="before")
    @classmethod
    def parse_invoice_date(cls, v):
        """Parse date from string if needed."""
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v


class BillUpdate(BaseModel):
    """Schema for updating a bill (all fields optional)."""
    vendor_id: Optional[UUID] = Field(None)
    invoice_number: Optional[str] = Field(None, max_length=100)
    invoice_date: Optional[date] = Field(None)
    due_date: Optional[date] = Field(None)
    subtotal: Optional[Decimal] = Field(None, ge=0)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    total_amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    status: Optional[BillStatus] = Field(None)
    notes: Optional[str] = Field(None)
    line_items: Optional[List[LineItemUpdate]] = Field(None, description="Updated line items")


class BillRead(BillBase):
    """Schema for reading a bill with full details."""
    id: UUID = Field(..., description="Bill ID")
    vendor_id: Optional[UUID] = Field(None, description="Vendor ID")
    vendor: Optional[VendorSummary] = Field(None, description="Vendor details")
    status: BillStatus = Field(..., description="Processing status")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Overall confidence")
    field_confidence: Optional[Dict[str, Any]] = Field(None, description="Per-field confidence")
    validation_errors: Optional[List[ValidationError]] = Field(None, description="Validation errors")
    is_duplicate: bool = Field(default=False, description="Duplicate flag")
    duplicate_of_id: Optional[UUID] = Field(None, description="Original bill ID if duplicate")
    image_url: str = Field(..., description="Image path/URL")
    bounding_boxes: Optional[Dict[str, BoundingBox]] = Field(None, description="Bounding boxes")
    task_id: Optional[str] = Field(None, description="Celery task ID")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in ms")
    ocr_engine: Optional[str] = Field(None, description="OCR engine used")
    approved_by: Optional[str] = Field(None, description="Approver")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    line_items: List[LineItemRead] = Field(default_factory=list, description="Line items")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {"from_attributes": True}
    
    @property
    def requires_review(self) -> bool:
        """Check if bill needs manual review."""
        return self.status in (BillStatus.NEEDS_REVIEW, BillStatus.DUPLICATE)
    
    @property
    def is_finalized(self) -> bool:
        """Check if bill is finalized."""
        return self.status in (BillStatus.APPROVED, BillStatus.POSTED)
    
    @property
    def low_confidence_fields(self) -> List[str]:
        """Get list of fields with low confidence."""
        if not self.field_confidence:
            return []
        return [k for k, v in self.field_confidence.items() if v < 0.85]


class BillSummary(BaseModel):
    """Brief bill info for lists."""
    id: UUID = Field(..., description="Bill ID")
    vendor_name: Optional[str] = Field(None, description="Vendor name")
    invoice_number: Optional[str] = Field(None, description="Invoice number")
    invoice_date: Optional[date] = Field(None, description="Invoice date")
    total_amount: Optional[Decimal] = Field(None, description="Total amount")
    status: BillStatus = Field(..., description="Status")
    confidence_score: Optional[float] = Field(None, description="Confidence score")
    has_errors: bool = Field(default=False, description="Has validation errors")
    created_at: datetime = Field(..., description="Created timestamp")
    
    model_config = {"from_attributes": True}


class BillList(BaseModel):
    """Schema for listing bills."""
    items: List[BillSummary] = Field(..., description="List of bills")
    total: int = Field(..., ge=0, description="Total count")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total pages")
    
    model_config = {"from_attributes": True}


# =============================================================================
# API Response Schemas
# =============================================================================

class BillUploadResponse(BaseModel):
    """Response when uploading a bill for processing."""
    task_id: str = Field(..., description="Task ID for status polling")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Initial status")
    message: str = Field(default="Bill uploaded successfully. Processing started.")
    estimated_time_seconds: int = Field(default=15, description="Estimated processing time")
    
    model_config = {"from_attributes": True}


class BillStatusResponse(BaseModel):
    """Response for bill processing status check."""
    task_id: str = Field(..., description="Task ID")
    status: TaskStatus = Field(..., description="Current status")
    progress: Optional[float] = Field(None, ge=0, le=1, description="Progress (0-1)")
    current_step: Optional[str] = Field(None, description="Current processing step")
    message: Optional[str] = Field(None, description="Human-readable status message")
    bill_id: Optional[UUID] = Field(None, description="Bill ID when completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    redirect_url: Optional[str] = Field(None, description="URL to view completed bill")
    stages_completed: Optional[List[str]] = Field(None, description="List of completed stages")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    model_config = {"from_attributes": True}


class BillApprovalRequest(BaseModel):
    """Request to approve a bill."""
    approved_by: str = Field(..., description="User who is approving")
    notes: Optional[str] = Field(None, description="Approval notes")


class BillCorrectionRequest(BaseModel):
    """Request to correct bill fields."""
    field_name: str = Field(..., description="Field to correct")
    old_value: Any = Field(..., description="Previous value")
    new_value: Any = Field(..., description="Corrected value")
    reason: Optional[str] = Field(None, description="Reason for correction")
