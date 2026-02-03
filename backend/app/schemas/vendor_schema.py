"""
BillAgent Pro - Vendor Schemas
===============================
Pydantic schemas for Vendor operations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class VendorBase(BaseModel):
    """Base vendor schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Vendor name")
    default_gl_code: Optional[str] = Field(None, max_length=50, description="Default GL code")
    address: Optional[str] = Field(None, max_length=500, description="Vendor address")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    tax_id: Optional[str] = Field(None, max_length=50, description="Tax ID")


class VendorCreate(VendorBase):
    """Schema for creating a new vendor."""
    pass


class VendorUpdate(BaseModel):
    """Schema for updating a vendor (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    default_gl_code: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = Field(None)
    tax_id: Optional[str] = Field(None, max_length=50)


class VendorRead(VendorBase):
    """Schema for reading a vendor."""
    id: UUID = Field(..., description="Vendor ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {"from_attributes": True}


class VendorList(BaseModel):
    """Schema for listing vendors."""
    items: List[VendorRead] = Field(..., description="List of vendors")
    total: int = Field(..., ge=0, description="Total count")
    
    model_config = {"from_attributes": True}


class VendorSummary(BaseModel):
    """Brief vendor info for embedding in other schemas."""
    id: UUID = Field(..., description="Vendor ID")
    name: str = Field(..., description="Vendor name")
    default_gl_code: Optional[str] = Field(None, description="Default GL code")
    
    model_config = {"from_attributes": True}
