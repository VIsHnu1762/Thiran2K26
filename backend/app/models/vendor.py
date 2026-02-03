"""
BillAgent Pro - Vendor Model
=============================
Represents vendors/suppliers from whom bills are received.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from ..database import Base

if TYPE_CHECKING:
    from .bill import Bill


class Vendor(Base):
    """
    Vendor/Supplier entity.
    
    Stores information about vendors and their default GL code
    for automatic categorization.
    """
    
    __tablename__ = "vendors"
    
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
    # Fields
    # -------------------------------------------------------------------------
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Vendor name"
    )
    
    # Default GL code for this vendor (learned from history)
    default_gl_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Default General Ledger code for this vendor"
    )
    
    # Contact information (optional)
    address: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Vendor address"
    )
    
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Vendor phone number"
    )
    
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Vendor email"
    )
    
    tax_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Vendor tax identification number"
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
    bills: Mapped[List["Bill"]] = relationship(
        "Bill",
        back_populates="vendor",
        lazy="selectin"
    )
    
    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index("idx_vendor_name_trgm", "name", postgresql_using="gin",
              postgresql_ops={"name": "gin_trgm_ops"}),
    )
    
    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<Vendor(id={self.id}, name='{self.name}')>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "default_gl_code": self.default_gl_code,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "tax_id": self.tax_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
