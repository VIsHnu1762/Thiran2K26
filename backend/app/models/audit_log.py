"""
BillAgent Pro - Audit Log Model
================================
Tracks all changes to bills for compliance and traceability.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any

from sqlalchemy import String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from ..database import Base

if TYPE_CHECKING:
    from .bill import Bill


class AuditLog(Base):
    """
    Audit Log entity.
    
    Records every action taken on a bill for compliance,
    debugging, and user activity tracking.
    """
    
    __tablename__ = "audit_logs"
    
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
    # Action Information
    # -------------------------------------------------------------------------
    action: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Action performed (e.g., 'CREATED', 'FIELD_UPDATED', 'APPROVED')"
    )
    
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Agent or user who performed the action"
    )
    
    # Detailed description of the action
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description of the action"
    )
    
    # -------------------------------------------------------------------------
    # Change Tracking
    # -------------------------------------------------------------------------
    field_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Name of the field that was changed"
    )
    
    old_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Previous value before the change"
    )
    
    new_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="New value after the change"
    )
    
    # -------------------------------------------------------------------------
    # Context
    # -------------------------------------------------------------------------
    # User information (if action was performed by a user)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User ID who performed the action"
    )
    
    user_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User email who performed the action"
    )
    
    # IP address for security auditing
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # Supports IPv6
        nullable=True,
        comment="IP address of the request"
    )
    
    # Request metadata
    request_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Request correlation ID"
    )
    
    # -------------------------------------------------------------------------
    # Additional Metadata
    # -------------------------------------------------------------------------
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional context (validation errors, confidence scores, etc.)"
    )
    
    # -------------------------------------------------------------------------
    # Timestamp
    # -------------------------------------------------------------------------
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    bill: Mapped["Bill"] = relationship(
        "Bill",
        back_populates="audit_logs"
    )
    
    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index("idx_audit_logs_bill_timestamp", "bill_id", "timestamp"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_agent", "agent_name"),
        Index("idx_audit_logs_timestamp", "timestamp"),
    )
    
    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action='{self.action}', agent='{self.agent_name}')>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "bill_id": str(self.bill_id),
            "action": self.action,
            "agent_name": self.agent_name,
            "description": self.description,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "ip_address": self.ip_address,
            "request_id": self.request_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


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
