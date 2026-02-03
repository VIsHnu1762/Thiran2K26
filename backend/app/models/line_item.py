"""
BillAgent Pro - Line Item Model
================================
Represents individual line items on a bill.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Dict, Any

from sqlalchemy import String, Numeric, Float, Text, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from ..database import Base

if TYPE_CHECKING:
    from .bill import Bill


class LineItem(Base):
    """
    Line Item entity.
    
    Represents a single item on a bill with quantity, price,
    and GL code assignment.
    """
    
    __tablename__ = "line_items"
    
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
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bills.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # -------------------------------------------------------------------------
    # Item Information
    # -------------------------------------------------------------------------
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Item description/name"
    )
    
    # Quantity (supports decimals for units like kg, liters)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False,
        default=Decimal("1.000"),
        comment="Quantity purchased"
    )
    
    # Unit of measure (optional)
    unit: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Unit of measure (e.g., pcs, kg, hr)"
    )
    
    # Price per unit
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Price per unit"
    )
    
    # Total for this line (quantity × unit_price)
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Line total (quantity × unit_price)"
    )
    
    # Tax on this item (optional, some bills show per-item tax)
    tax_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Tax amount for this line item"
    )
    
    # -------------------------------------------------------------------------
    # Accounting
    # -------------------------------------------------------------------------
    gl_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="General Ledger code for this item"
    )
    
    gl_code_source: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="How GL code was assigned (vendor_default, keyword, llm, manual)"
    )
    
    # -------------------------------------------------------------------------
    # OCR Confidence
    # -------------------------------------------------------------------------
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="OCR confidence for this line item (0.0 to 1.0)"
    )
    
    field_confidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Per-field confidence (description, quantity, price, etc.)"
    )
    
    # -------------------------------------------------------------------------
    # Bounding Box (for UI highlighting)
    # -------------------------------------------------------------------------
    bounding_box: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Bounding box coordinates {x, y, width, height}"
    )
    
    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    is_verified: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether this line item has been manually verified"
    )
    
    has_math_error: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether qty × price != total"
    )
    
    # -------------------------------------------------------------------------
    # Order (for maintaining original bill layout)
    # -------------------------------------------------------------------------
    sort_order: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Order of item on the bill"
    )
    
    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    bill: Mapped["Bill"] = relationship(
        "Bill",
        back_populates="line_items"
    )
    
    # -------------------------------------------------------------------------
    # Indexes & Constraints
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index("idx_line_items_bill_order", "bill_id", "sort_order"),
        Index("idx_line_items_gl_code", "gl_code"),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_line_item_confidence_range"
        ),
    )
    
    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<LineItem(id={self.id}, description='{self.description[:30]}...', total={self.total_price})>"
    
    @property
    def calculated_total(self) -> Decimal:
        """Calculate what the total should be."""
        return self.quantity * self.unit_price
    
    @property
    def math_is_correct(self) -> bool:
        """Check if quantity × unit_price equals total_price (within tolerance)."""
        tolerance = Decimal("0.01")
        return abs(self.calculated_total - self.total_price) <= tolerance
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "bill_id": str(self.bill_id),
            "description": self.description,
            "quantity": float(self.quantity),
            "unit": self.unit,
            "unit_price": float(self.unit_price),
            "total_price": float(self.total_price),
            "tax_amount": float(self.tax_amount) if self.tax_amount else None,
            "gl_code": self.gl_code,
            "gl_code_source": self.gl_code_source,
            "confidence_score": self.confidence_score,
            "field_confidence": self.field_confidence,
            "bounding_box": self.bounding_box,
            "is_verified": self.is_verified,
            "has_math_error": self.has_math_error,
            "sort_order": self.sort_order,
        }
