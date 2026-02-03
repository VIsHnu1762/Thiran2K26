"""
BillAgent Pro - Line Item Schemas
==================================
Pydantic schemas for Line Item operations.
"""

from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from .common import BoundingBox


class LineItemBase(BaseModel):
    """Base line item schema with common fields."""
    description: str = Field(..., min_length=1, description="Item description")
    quantity: Decimal = Field(default=Decimal("1.000"), ge=0, description="Quantity")
    unit: Optional[str] = Field(None, max_length=50, description="Unit of measure")
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0, description="Price per unit")
    total_price: Decimal = Field(default=Decimal("0.00"), ge=0, description="Line total")
    tax_amount: Optional[Decimal] = Field(None, ge=0, description="Tax amount")
    gl_code: Optional[str] = Field(None, max_length=50, description="GL code")


class LineItemCreate(LineItemBase):
    """Schema for creating a line item."""
    bill_id: Optional[UUID] = Field(None, description="Parent bill ID")
    sort_order: int = Field(default=0, ge=0, description="Sort order")
    
    @field_validator("total_price", mode="before")
    @classmethod
    def calculate_total_if_missing(cls, v, info):
        """Calculate total from quantity × unit_price if not provided."""
        if v is None or v == Decimal("0.00"):
            data = info.data
            qty = data.get("quantity", Decimal("1"))
            price = data.get("unit_price", Decimal("0"))
            if qty and price:
                return qty * price
        return v


class LineItemUpdate(BaseModel):
    """Schema for updating a line item (all fields optional)."""
    description: Optional[str] = Field(None, min_length=1)
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=50)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    total_price: Optional[Decimal] = Field(None, ge=0)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    gl_code: Optional[str] = Field(None, max_length=50)
    is_verified: Optional[bool] = Field(None)
    sort_order: Optional[int] = Field(None, ge=0)


class LineItemRead(LineItemBase):
    """Schema for reading a line item."""
    id: UUID = Field(..., description="Line item ID")
    bill_id: UUID = Field(..., description="Parent bill ID")
    gl_code_source: Optional[str] = Field(None, description="How GL code was assigned")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="OCR confidence")
    field_confidence: Optional[Dict[str, Any]] = Field(None, description="Per-field confidence")
    bounding_box: Optional[BoundingBox] = Field(None, description="Bounding box coordinates")
    is_verified: bool = Field(default=False, description="Manually verified")
    has_math_error: bool = Field(default=False, description="Math error detected")
    sort_order: int = Field(default=0, description="Sort order")
    
    model_config = {"from_attributes": True}
    
    @property
    def calculated_total(self) -> Decimal:
        """What the total should be."""
        return self.quantity * self.unit_price
    
    @property
    def needs_attention(self) -> bool:
        """Whether this item needs human attention."""
        return (
            self.has_math_error or 
            (self.confidence_score is not None and self.confidence_score < 0.85)
        )
