"""
BillAgent Pro - Audit Log Schemas
==================================
Pydantic schemas for Audit Log operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class AuditLogBase(BaseModel):
    """Base audit log schema."""
    action: str = Field(..., max_length=255, description="Action performed")
    agent_name: str = Field(..., max_length=100, description="Agent or user name")
    description: Optional[str] = Field(None, description="Action description")
    field_name: Optional[str] = Field(None, max_length=100, description="Changed field")
    old_value: Optional[Dict[str, Any]] = Field(None, description="Previous value")
    new_value: Optional[Dict[str, Any]] = Field(None, description="New value")


class AuditLogCreate(AuditLogBase):
    """Schema for creating an audit log entry."""
    bill_id: UUID = Field(..., description="Bill ID")
    user_id: Optional[str] = Field(None, description="User ID")
    user_email: Optional[str] = Field(None, description="User email")
    ip_address: Optional[str] = Field(None, description="IP address")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AuditLogRead(AuditLogBase):
    """Schema for reading an audit log entry."""
    id: UUID = Field(..., description="Audit log ID")
    bill_id: UUID = Field(..., description="Bill ID")
    user_id: Optional[str] = Field(None, description="User ID")
    user_email: Optional[str] = Field(None, description="User email")
    ip_address: Optional[str] = Field(None, description="IP address")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    timestamp: datetime = Field(..., description="Action timestamp")
    
    model_config = {"from_attributes": True}


class AuditLogList(BaseModel):
    """Schema for listing audit logs."""
    items: List[AuditLogRead] = Field(..., description="List of audit logs")
    total: int = Field(..., ge=0, description="Total count")
    bill_id: UUID = Field(..., description="Bill ID")
    
    model_config = {"from_attributes": True}


# =============================================================================
# Audit Action Constants
# =============================================================================
class AuditAction:
    """Standard audit action names."""
    
    # Bill lifecycle
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    
    # Processing stages
    OCR_STARTED = "OCR_STARTED"
    OCR_COMPLETED = "OCR_COMPLETED"
    OCR_FAILED = "OCR_FAILED"
    
    # Agent actions
    DIGITIZER_COMPLETED = "DIGITIZER_COMPLETED"
    AUDITOR_VALIDATED = "AUDITOR_VALIDATED"
    AUDITOR_FAILED = "AUDITOR_FAILED"
    CONTROLLER_CHECKED = "CONTROLLER_CHECKED"
    DUPLICATE_DETECTED = "DUPLICATE_DETECTED"
    ACCOUNTANT_GL_ASSIGNED = "ACCOUNTANT_GL_ASSIGNED"
    
    # User actions
    FIELD_CORRECTED = "FIELD_CORRECTED"
    LINE_ITEM_ADDED = "LINE_ITEM_ADDED"
    LINE_ITEM_REMOVED = "LINE_ITEM_REMOVED"
    VERIFIED = "VERIFIED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    POSTED = "POSTED"
    
    # Status changes
    STATUS_CHANGED = "STATUS_CHANGED"
