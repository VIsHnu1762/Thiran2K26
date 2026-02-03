"""
BillAgent Pro - Vendor Repository
==================================
Database operations for Vendor entities.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Vendor


class VendorRepository:
    """Repository for Vendor database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, vendor: Vendor) -> Vendor:
        """Create a new vendor."""
        self.db.add(vendor)
        await self.db.commit()
        await self.db.refresh(vendor)
        return vendor
    
    async def get_by_id(self, vendor_id: UUID) -> Optional[Vendor]:
        """Get a vendor by ID."""
        result = await self.db.execute(
            select(Vendor).where(Vendor.id == vendor_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Vendor]:
        """Get a vendor by exact name match."""
        result = await self.db.execute(
            select(Vendor).where(Vendor.name == name)
        )
        return result.scalar_one_or_none()
    
    async def search_by_name(self, name: str, limit: int = 10) -> List[Vendor]:
        """Search vendors by name (fuzzy match)."""
        result = await self.db.execute(
            select(Vendor)
            .where(Vendor.name.ilike(f"%{name}%"))
            .order_by(Vendor.name)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def update(self, vendor: Vendor) -> Vendor:
        """Update a vendor."""
        vendor.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(vendor)
        return vendor
    
    async def delete(self, vendor_id: UUID) -> bool:
        """Delete a vendor."""
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return False
        
        await self.db.delete(vendor)
        await self.db.commit()
        return True
    
    async def list_vendors(
        self,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None
    ) -> Tuple[List[Vendor], int]:
        """List vendors with pagination."""
        query = select(Vendor)
        count_query = select(func.count(Vendor.id))
        
        if search:
            search_filter = or_(
                Vendor.name.ilike(f"%{search}%"),
                Vendor.email.ilike(f"%{search}%") if search else False
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(Vendor.name).offset(offset).limit(page_size)
        
        result = await self.db.execute(query)
        vendors = list(result.scalars().all())
        
        return vendors, total
    
    async def get_all(self) -> List[Vendor]:
        """Get all vendors (for dropdowns, etc.)."""
        result = await self.db.execute(
            select(Vendor).order_by(Vendor.name)
        )
        return list(result.scalars().all())
    
    async def get_or_create(self, name: str, **kwargs) -> Tuple[Vendor, bool]:
        """Get existing vendor or create new one.
        
        Returns (vendor, created) tuple where created is True if new.
        """
        existing = await self.get_by_name(name)
        if existing:
            return existing, False
        
        vendor = Vendor(name=name, **kwargs)
        await self.create(vendor)
        return vendor, True
    
    async def get_top_vendors(self, limit: int = 10) -> List[dict]:
        """Get top vendors by bill count."""
        from ..models import Bill
        
        result = await self.db.execute(
            select(
                Vendor.id,
                Vendor.name,
                func.count(Bill.id).label("bill_count"),
                func.sum(Bill.total_amount).label("total_amount")
            )
            .join(Bill, Bill.vendor_id == Vendor.id)
            .group_by(Vendor.id, Vendor.name)
            .order_by(func.count(Bill.id).desc())
            .limit(limit)
        )
        
        return [
            {
                "id": str(row.id),
                "name": row.name,
                "bill_count": row.bill_count,
                "total_amount": float(row.total_amount or 0)
            }
            for row in result
        ]
