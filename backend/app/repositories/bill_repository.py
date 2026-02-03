"""
BillAgent Pro - Bill Repository
================================
Database operations for Bill entities.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Bill, LineItem, AuditLog, Vendor
from ..models.bill import BillStatus


class BillRepository:
    """Repository for Bill database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, bill: Bill) -> Bill:
        """Create a new bill."""
        self.db.add(bill)
        await self.db.commit()
        await self.db.refresh(bill)
        return bill
    
    async def get_by_id(self, bill_id: UUID, include_items: bool = True) -> Optional[Bill]:
        """Get a bill by ID."""
        query = select(Bill)
        if include_items:
            query = query.options(
                selectinload(Bill.line_items),
                selectinload(Bill.vendor),
                selectinload(Bill.audit_logs)
            )
        query = query.where(Bill.id == bill_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_task_id(self, task_id: str) -> Optional[Bill]:
        """Get a bill by Celery task ID."""
        result = await self.db.execute(
            select(Bill).where(Bill.task_id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, bill: Bill) -> Bill:
        """Update a bill."""
        bill.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(bill)
        return bill
    
    async def delete(self, bill_id: UUID) -> bool:
        """Soft delete a bill (or hard delete if needed)."""
        bill = await self.get_by_id(bill_id, include_items=False)
        if not bill:
            return False
        
        # Option 1: Hard delete
        await self.db.delete(bill)
        await self.db.commit()
        return True
    
    async def list_bills(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[BillStatus] = None,
        vendor_id: Optional[UUID] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[List[Bill], int]:
        """List bills with pagination and filtering."""
        # Build query
        query = select(Bill).options(selectinload(Bill.vendor))
        count_query = select(func.count(Bill.id))
        
        # Apply filters
        filters = []
        if status:
            filters.append(Bill.status == status)
        if vendor_id:
            filters.append(Bill.vendor_id == vendor_id)
        if search:
            filters.append(
                or_(
                    Bill.invoice_number.ilike(f"%{search}%"),
                    Bill.vendor.has(Vendor.name.ilike(f"%{search}%"))
                )
            )
        if date_from:
            filters.append(Bill.invoice_date >= date_from.date())
        if date_to:
            filters.append(Bill.invoice_date <= date_to.date())
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(desc(Bill.created_at)).offset(offset).limit(page_size)
        
        # Execute
        result = await self.db.execute(query)
        bills = list(result.scalars().all())
        
        return bills, total
    
    async def find_duplicates(
        self,
        vendor_id: Optional[UUID],
        invoice_number: Optional[str],
        total_amount: Optional[Decimal],
        invoice_date: Optional[datetime] = None
    ) -> List[Bill]:
        """Find potential duplicate bills."""
        if not vendor_id and not invoice_number:
            return []
        
        filters = []
        if vendor_id:
            filters.append(Bill.vendor_id == vendor_id)
        if invoice_number:
            filters.append(Bill.invoice_number == invoice_number)
        if total_amount:
            # Allow small tolerance for amount matching
            tolerance = Decimal("0.01")
            filters.append(
                and_(
                    Bill.total_amount >= total_amount - tolerance,
                    Bill.total_amount <= total_amount + tolerance
                )
            )
        
        query = select(Bill).where(
            and_(
                *filters,
                Bill.status.not_in([BillStatus.FAILED, BillStatus.DUPLICATE])
            )
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_bills_needing_review(self, limit: int = 50) -> List[Bill]:
        """Get bills that need manual review."""
        result = await self.db.execute(
            select(Bill)
            .options(selectinload(Bill.vendor), selectinload(Bill.line_items))
            .where(Bill.status == BillStatus.NEEDS_REVIEW)
            .order_by(Bill.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_processing_bills(self) -> List[Bill]:
        """Get bills currently being processed."""
        result = await self.db.execute(
            select(Bill)
            .where(Bill.status == BillStatus.PROCESSING)
            .order_by(Bill.created_at)
        )
        return list(result.scalars().all())
    
    async def update_status(
        self,
        bill_id: UUID,
        new_status: BillStatus,
        agent_name: str = "System",
        reason: Optional[str] = None
    ) -> Optional[Bill]:
        """Update bill status with audit logging."""
        bill = await self.get_by_id(bill_id, include_items=False)
        if not bill:
            return None
        
        old_status = bill.status
        bill.status = new_status
        bill.updated_at = datetime.utcnow()
        
        # Create audit log
        audit_log = AuditLog(
            bill_id=bill_id,
            action="STATUS_CHANGED",
            agent_name=agent_name,
            description=reason or f"Status changed from {old_status.value} to {new_status.value}",
            old_value={"status": old_status.value},
            new_value={"status": new_status.value}
        )
        self.db.add(audit_log)
        
        await self.db.commit()
        await self.db.refresh(bill)
        return bill
    
    async def add_line_item(self, bill_id: UUID, line_item: LineItem) -> LineItem:
        """Add a line item to a bill."""
        line_item.bill_id = bill_id
        self.db.add(line_item)
        
        # Update bill totals
        bill = await self.get_by_id(bill_id, include_items=True)
        if bill:
            bill.subtotal = sum(item.total_price for item in bill.line_items)
            bill.total_amount = bill.subtotal + (bill.tax_amount or Decimal("0"))
            bill.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(line_item)
        return line_item
    
    async def get_dashboard_stats(self) -> dict:
        """Get dashboard statistics."""
        # Total bills
        total_result = await self.db.execute(select(func.count(Bill.id)))
        total_bills = total_result.scalar() or 0
        
        # Pending review
        pending_result = await self.db.execute(
            select(func.count(Bill.id)).where(Bill.status == BillStatus.NEEDS_REVIEW)
        )
        pending_review = pending_result.scalar() or 0
        
        # Approved today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        approved_result = await self.db.execute(
            select(func.count(Bill.id)).where(
                and_(
                    Bill.status == BillStatus.APPROVED,
                    Bill.approved_at >= today_start
                )
            )
        )
        approved_today = approved_result.scalar() or 0
        
        # Total amount
        amount_result = await self.db.execute(
            select(func.sum(Bill.total_amount)).where(
                Bill.status.in_([BillStatus.APPROVED, BillStatus.POSTED])
            )
        )
        total_amount = float(amount_result.scalar() or 0)
        
        # Average confidence
        confidence_result = await self.db.execute(
            select(func.avg(Bill.confidence_score)).where(Bill.confidence_score.isnot(None))
        )
        avg_confidence = float(confidence_result.scalar() or 0)
        
        return {
            "total_bills": total_bills,
            "pending_review": pending_review,
            "approved_today": approved_today,
            "total_amount": total_amount,
            "average_confidence": avg_confidence,
        }
