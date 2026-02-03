"""
BillAgent Pro - Bill Model
===========================
Represents the main bill/invoice entity.
"""

import uuid
import enum
from datetime import datetime, date
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional, Dict, Any

from sqlalchemy import (
    String, DateTime, Date, Numeric, Float, Text, Enum, 
    ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from ..database import Base

if TYPE_CHECKING:
    from .vendor import Vendor
    from .line_item import LineItem
    from .audit_log import AuditLog


class BillStatus(str, enum.Enum):
    """Bill processing status."""
    PROCESSING = "PROCESSING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    POSTED = "POSTED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class Bill(Base):
    """
    Bill/Invoice entity.
    
    Represents a digitized bill with extracted data, confidence scores,
    validation status, and audit trail.
    """
    
    __tablename__ = "bills"
    
    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # -------------------------------------------------------------------------
    # Foreign Keys
    # -------------------------------------------------------------------------
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # -------------------------------------------------------------------------
    # Invoice Information
    # -------------------------------------------------------------------------
    invoice_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Invoice number from the bill"
    )
    
    invoice_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date on the invoice"
    )
    
    due_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Payment due date"
    )
    
    # -------------------------------------------------------------------------
    # Financial Data (using Decimal for precision)
    # -------------------------------------------------------------------------
    subtotal: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Sum of all line items before tax"
    )
    
    tax_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        default=Decimal("0.00"),
        comment="Total tax amount"
    )
    
    total_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Grand total (subtotal + tax)"
    )
    
    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False,
        comment="Currency code (ISO 4217)"
    )
    
    # -------------------------------------------------------------------------
    # Processing Status
    # -------------------------------------------------------------------------
    status: Mapped[BillStatus] = mapped_column(
        Enum(BillStatus),
        default=BillStatus.PROCESSING,
        nullable=False,
        index=True,
        comment="Current processing status"
    )
    
    # -------------------------------------------------------------------------
    # Confidence Scores
    # -------------------------------------------------------------------------
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Overall OCR confidence (0.0 to 1.0)"
    )
    
    field_confidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Per-field confidence scores"
    )
    
    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    validation_errors: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="List of validation errors from auditor agent"
    )
    
    is_duplicate: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether this bill is a potential duplicate"
    )
    
    duplicate_of_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Reference to the original bill if duplicate"
    )
    
    # -------------------------------------------------------------------------
    # Image & OCR Data
    # -------------------------------------------------------------------------
    image_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Path or URL to the bill image"
    )
    
    ocr_raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Raw OCR response for debugging"
    )
    
    bounding_boxes: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Bounding box coordinates for UI highlighting"
    )
    
    # -------------------------------------------------------------------------
    # Processing Metadata
    # -------------------------------------------------------------------------
    task_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Celery task ID for async processing"
    )
    
    processing_time_ms: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Total processing time in milliseconds"
    )
    
    ocr_engine: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="OCR engine used (mistral, gpt4, easyocr)"
    )
    
    # -------------------------------------------------------------------------
    # User Actions
    # -------------------------------------------------------------------------
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User who approved the bill"
    )
    
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp of approval"
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User notes or comments"
    )
    
    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    vendor: Mapped[Optional["Vendor"]] = relationship(
        "Vendor",
        back_populates="bills",
        lazy="selectin"
    )
    
    line_items: Mapped[List["LineItem"]] = relationship(
        "LineItem",
        back_populates="bill",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="bill",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    
    # -------------------------------------------------------------------------
    # Indexes & Constraints
    # -------------------------------------------------------------------------
    __table_args__ = (
        # Composite index for duplicate detection
        Index("idx_bills_duplicate_check", "vendor_id", "invoice_number", "total_amount"),
        # Index for status filtering
        Index("idx_bills_status", "status"),
        # Index for date range queries
        Index("idx_bills_invoice_date", "invoice_date"),
        # Confidence score constraint
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_confidence_score_range"
        ),
    )
    
    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<Bill(id={self.id}, invoice={self.invoice_number}, status={self.status})>"
    
    @property
    def requires_review(self) -> bool:
        """Check if bill needs manual review."""
        return self.status in (BillStatus.NEEDS_REVIEW, BillStatus.DUPLICATE)
    
    @property
    def is_finalized(self) -> bool:
        """Check if bill is finalized (approved or posted)."""
        return self.status in (BillStatus.APPROVED, BillStatus.POSTED)
    
    def to_dict(self, include_line_items: bool = True) -> dict:
        """Convert to dictionary."""
        result = {
            "id": str(self.id),
            "vendor_id": str(self.vendor_id) if self.vendor_id else None,
            "vendor": self.vendor.to_dict() if self.vendor else None,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "subtotal": float(self.subtotal) if self.subtotal else None,
            "tax_amount": float(self.tax_amount) if self.tax_amount else None,
            "total_amount": float(self.total_amount) if self.total_amount else None,
            "currency": self.currency,
            "status": self.status.value,
            "confidence_score": self.confidence_score,
            "field_confidence": self.field_confidence,
            "validation_errors": self.validation_errors,
            "is_duplicate": self.is_duplicate,
            "image_url": self.image_url,
            "bounding_boxes": self.bounding_boxes,
            "processing_time_ms": self.processing_time_ms,
            "ocr_engine": self.ocr_engine,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if include_line_items:
            result["line_items"] = [item.to_dict() for item in self.line_items]
        
        return result
