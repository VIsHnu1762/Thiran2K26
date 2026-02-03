"""
BillAgent Pro - GL Code Model
==============================
General Ledger codes for expense categorization.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, Text

from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class GLCode(Base):
    """
    General Ledger Code entity.
    
    Represents expense categories for accounting integration.
    """
    
    __tablename__ = "gl_codes"
    
    # -------------------------------------------------------------------------
    # Primary Key (GL Code itself is the primary key)
    # -------------------------------------------------------------------------
    code: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="GL code (e.g., '5001', '5001-01')"
    )
    
    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="GL code name (e.g., 'Office Supplies')"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of this GL code"
    )
    
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="EXPENSE",
        comment="Category (EXPENSE, ASSET, LIABILITY, EQUITY, REVENUE)"
    )
    
    parent_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Parent GL code for hierarchical structure"
    )
    
    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this GL code is active"
    )
    
    # -------------------------------------------------------------------------
    # Keywords for automatic matching
    # -------------------------------------------------------------------------
    keywords: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated keywords for automatic GL code matching"
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
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<GLCode(code='{self.code}', name='{self.name}')>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parent_code": self.parent_code,
            "is_active": self.is_active,
            "keywords": self.keywords.split(",") if self.keywords else [],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# =============================================================================
# Default GL Codes (to be seeded)
# =============================================================================
DEFAULT_GL_CODES = [
    {
        "code": "5001",
        "name": "Office Supplies",
        "category": "EXPENSE",
        "keywords": "office,supplies,paper,pen,pencil,stapler,folder,stationery,printer"
    },
    {
        "code": "5002",
        "name": "Travel & Transportation",
        "category": "EXPENSE",
        "keywords": "travel,transport,fuel,gas,petrol,diesel,taxi,uber,flight,train,bus"
    },
    {
        "code": "5003",
        "name": "Utilities",
        "category": "EXPENSE",
        "keywords": "utility,utilities,electric,electricity,water,gas,internet,phone,telecom"
    },
    {
        "code": "5004",
        "name": "Professional Services",
        "category": "EXPENSE",
        "keywords": "professional,consulting,legal,accounting,audit,advisory,service"
    },
    {
        "code": "5005",
        "name": "Maintenance & Repairs",
        "category": "EXPENSE",
        "keywords": "maintenance,repair,fix,service,cleaning,janitorial"
    },
    {
        "code": "5006",
        "name": "Raw Materials",
        "category": "EXPENSE",
        "keywords": "raw,material,ingredient,component,supply,manufacturing"
    },
    {
        "code": "5007",
        "name": "Inventory Purchases",
        "category": "EXPENSE",
        "keywords": "inventory,stock,goods,merchandise,product,purchase"
    },
    {
        "code": "5008",
        "name": "Marketing & Advertising",
        "category": "EXPENSE",
        "keywords": "marketing,advertising,ad,promotion,campaign,media,print"
    },
    {
        "code": "5009",
        "name": "Insurance",
        "category": "EXPENSE",
        "keywords": "insurance,premium,coverage,policy"
    },
    {
        "code": "5010",
        "name": "Rent & Lease",
        "category": "EXPENSE",
        "keywords": "rent,lease,rental,property,office,warehouse"
    },
    {
        "code": "5011",
        "name": "Equipment",
        "category": "EXPENSE",
        "keywords": "equipment,machine,machinery,tool,hardware,computer"
    },
    {
        "code": "5012",
        "name": "Software & Subscriptions",
        "category": "EXPENSE",
        "keywords": "software,subscription,license,saas,cloud,app"
    },
    {
        "code": "5099",
        "name": "Miscellaneous Expenses",
        "category": "EXPENSE",
        "keywords": "misc,miscellaneous,other"
    },
]
