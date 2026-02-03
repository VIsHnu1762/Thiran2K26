"""
BillAgent Pro - GL Code Schemas
================================
Pydantic schemas for GL Code operations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class GLCodeBase(BaseModel):
    """Base GL code schema."""
    code: str = Field(..., min_length=1, max_length=50, description="GL code")
    name: str = Field(..., min_length=1, max_length=255, description="GL code name")
    category: Optional[str] = Field(None, max_length=100, description="Expense category")
    description: Optional[str] = Field(None, description="Description")
    is_active: bool = Field(default=True, description="Whether active")


class GLCodeCreate(GLCodeBase):
    """Schema for creating a GL code."""
    keywords: List[str] = Field(default_factory=list, description="Keywords for matching")


class GLCodeUpdate(BaseModel):
    """Schema for updating a GL code (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None)
    keywords: Optional[List[str]] = Field(None)
    is_active: Optional[bool] = Field(None)


class GLCodeRead(GLCodeBase):
    """Schema for reading a GL code."""
    keywords: List[str] = Field(default_factory=list, description="Keywords for matching")
    
    model_config = {"from_attributes": True}


class GLCodeList(BaseModel):
    """Schema for listing GL codes."""
    items: List[GLCodeRead] = Field(..., description="List of GL codes")
    total: int = Field(..., ge=0, description="Total count")
    
    model_config = {"from_attributes": True}


class GLCodeMatch(BaseModel):
    """Result of GL code matching."""
    code: str = Field(..., description="Matched GL code")
    name: str = Field(..., description="GL code name")
    confidence: float = Field(..., ge=0, le=1, description="Match confidence")
    matched_keywords: List[str] = Field(default_factory=list, description="Matched keywords")
    source: str = Field(..., description="Source of match: 'keyword', 'vendor_default', 'ml_suggestion'")
    
    model_config = {"from_attributes": True}
