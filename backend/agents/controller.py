"""
BillAgent Pro - Controller Agent
==================================
Agent 3: Duplicate detection and bill deduplication.
Checks incoming bills against existing records to prevent duplicates.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


@dataclass
class DuplicateMatch:
    """A potential duplicate bill match."""
    bill_id: UUID
    invoice_number: Optional[str]
    vendor_id: Optional[UUID]
    vendor_name: Optional[str]
    total_amount: Optional[Decimal]
    invoice_date: Optional[date]
    created_at: Optional[str]
    match_score: float  # 0.0 to 1.0
    match_reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "bill_id": str(self.bill_id),
            "invoice_number": self.invoice_number,
            "vendor_id": str(self.vendor_id) if self.vendor_id else None,
            "vendor_name": self.vendor_name,
            "total_amount": str(self.total_amount) if self.total_amount else None,
            "invoice_date": str(self.invoice_date) if self.invoice_date else None,
            "created_at": self.created_at,
            "match_score": self.match_score,
            "match_reasons": self.match_reasons,
        }


@dataclass
class DuplicateCheckResult:
    """Result of duplicate detection check."""
    is_duplicate: bool
    potential_duplicates: List[DuplicateMatch] = field(default_factory=list)
    highest_match_score: float = 0.0
    suggested_status: str = "APPROVED"
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_duplicate": self.is_duplicate,
            "potential_duplicates": [d.to_dict() for d in self.potential_duplicates],
            "highest_match_score": self.highest_match_score,
            "suggested_status": self.suggested_status,
            "message": self.message,
        }


class ControllerAgent:
    """
    Agent 3: Controller Agent
    
    Responsible for:
    - Detecting duplicate bills based on vendor_id, invoice_number, and total_amount
    - Scoring potential duplicates based on match criteria
    - Flagging bills that need manual review
    
    Duplicate detection criteria:
    1. Exact match: vendor_id + invoice_number + total_amount (within tolerance)
    2. High confidence: vendor_id + invoice_number
    3. Medium confidence: vendor_id + total_amount (within date range)
    4. Low confidence: invoice_number + total_amount
    """
    
    # Threshold for amount matching tolerance
    AMOUNT_TOLERANCE = Decimal("0.01")
    
    # Score thresholds
    DUPLICATE_THRESHOLD = 0.8  # Score >= this is considered a duplicate
    REVIEW_THRESHOLD = 0.5    # Score >= this needs review
    
    # Date range for duplicate detection (days)
    DATE_RANGE_DAYS = 30
    
    def __init__(
        self,
        amount_tolerance: Decimal = Decimal("0.01"),
        duplicate_threshold: float = 0.8,
        review_threshold: float = 0.5,
        date_range_days: int = 30,
    ):
        """
        Initialize the Controller Agent.
        
        Args:
            amount_tolerance: Tolerance for amount matching
            duplicate_threshold: Score threshold for considering a definite duplicate
            review_threshold: Score threshold for flagging for review
            date_range_days: Number of days to look back for duplicates
        """
        self.AMOUNT_TOLERANCE = amount_tolerance
        self.DUPLICATE_THRESHOLD = duplicate_threshold
        self.REVIEW_THRESHOLD = review_threshold
        self.DATE_RANGE_DAYS = date_range_days
        
        logger.info(
            f"ControllerAgent initialized with tolerance={amount_tolerance}, "
            f"duplicate_threshold={duplicate_threshold}"
        )
    
    async def check_duplicate(
        self,
        bill_data: Dict[str, Any],
        db: AsyncSession,
        exclude_bill_id: Optional[UUID] = None,
    ) -> DuplicateCheckResult:
        """
        Check if a bill is a potential duplicate.
        
        Args:
            bill_data: Dictionary containing:
                - vendor_id: UUID (optional)
                - invoice_number: str (optional)
                - total_amount: Decimal
                - invoice_date: date (optional)
            db: AsyncSession for database queries
            exclude_bill_id: Bill ID to exclude from results (for updates)
        
        Returns:
            DuplicateCheckResult with potential duplicates and suggested status
        """
        # Import models here to avoid circular imports
        from app.models import Bill, Vendor
        from app.models.bill import BillStatus
        
        vendor_id = bill_data.get("vendor_id")
        invoice_number = bill_data.get("invoice_number")
        total_amount = self._to_decimal(bill_data.get("total_amount"))
        invoice_date = self._to_date(bill_data.get("invoice_date"))
        
        logger.info(
            f"Checking duplicates for: vendor_id={vendor_id}, "
            f"invoice_number={invoice_number}, total_amount={total_amount}"
        )
        
        # If we don't have enough data to check, return no duplicates
        if not vendor_id and not invoice_number and not total_amount:
            logger.info("Insufficient data for duplicate check")
            return DuplicateCheckResult(
                is_duplicate=False,
                message="Insufficient data for duplicate check"
            )
        
        # Build query to find potential duplicates
        potential_matches: List[DuplicateMatch] = []
        
        # Query 1: Check for exact match (vendor + invoice number + amount)
        if vendor_id and invoice_number and total_amount:
            exact_matches = await self._find_exact_matches(
                db, vendor_id, invoice_number, total_amount, 
                exclude_bill_id, Bill, BillStatus
            )
            potential_matches.extend(exact_matches)
        
        # Query 2: Check vendor + invoice number match
        if vendor_id and invoice_number:
            vendor_invoice_matches = await self._find_vendor_invoice_matches(
                db, vendor_id, invoice_number, exclude_bill_id, Bill, BillStatus
            )
            # Only add if not already in list
            for match in vendor_invoice_matches:
                if not any(m.bill_id == match.bill_id for m in potential_matches):
                    potential_matches.append(match)
        
        # Query 3: Check vendor + amount match (within date range)
        if vendor_id and total_amount and invoice_date:
            vendor_amount_matches = await self._find_vendor_amount_matches(
                db, vendor_id, total_amount, invoice_date, 
                exclude_bill_id, Bill, BillStatus
            )
            for match in vendor_amount_matches:
                if not any(m.bill_id == match.bill_id for m in potential_matches):
                    potential_matches.append(match)
        
        # Query 4: Check invoice number + amount match
        if invoice_number and total_amount:
            invoice_amount_matches = await self._find_invoice_amount_matches(
                db, invoice_number, total_amount, exclude_bill_id, Bill, BillStatus
            )
            for match in invoice_amount_matches:
                if not any(m.bill_id == match.bill_id for m in potential_matches):
                    potential_matches.append(match)
        
        # Sort by match score (highest first)
        potential_matches.sort(key=lambda x: x.match_score, reverse=True)
        
        # Determine if it's a duplicate
        highest_score = max((m.match_score for m in potential_matches), default=0.0)
        
        is_duplicate = highest_score >= self.DUPLICATE_THRESHOLD
        needs_review = highest_score >= self.REVIEW_THRESHOLD
        
        if is_duplicate:
            suggested_status = "DUPLICATE"
            message = f"High confidence duplicate detected (score: {highest_score:.2f})"
        elif needs_review:
            suggested_status = "NEEDS_REVIEW"
            message = f"Potential duplicates found (score: {highest_score:.2f})"
        else:
            suggested_status = "APPROVED"
            message = "No duplicates found"
        
        logger.info(
            f"Duplicate check complete: is_duplicate={is_duplicate}, "
            f"matches={len(potential_matches)}, highest_score={highest_score:.2f}"
        )
        
        return DuplicateCheckResult(
            is_duplicate=is_duplicate,
            potential_duplicates=potential_matches,
            highest_match_score=highest_score,
            suggested_status=suggested_status,
            message=message,
        )
    
    async def _find_exact_matches(
        self,
        db: AsyncSession,
        vendor_id: UUID,
        invoice_number: str,
        total_amount: Decimal,
        exclude_bill_id: Optional[UUID],
        Bill,
        BillStatus,
    ) -> List[DuplicateMatch]:
        """Find exact matches (vendor + invoice + amount)."""
        matches = []
        
        query = (
            select(Bill)
            .options(selectinload(Bill.vendor))
            .where(
                and_(
                    Bill.vendor_id == vendor_id,
                    Bill.invoice_number == invoice_number,
                    Bill.total_amount >= total_amount - self.AMOUNT_TOLERANCE,
                    Bill.total_amount <= total_amount + self.AMOUNT_TOLERANCE,
                    Bill.status.not_in([BillStatus.FAILED, BillStatus.DUPLICATE]),
                )
            )
        )
        
        if exclude_bill_id:
            query = query.where(Bill.id != exclude_bill_id)
        
        result = await db.execute(query)
        bills = result.scalars().all()
        
        for bill in bills:
            matches.append(DuplicateMatch(
                bill_id=bill.id,
                invoice_number=bill.invoice_number,
                vendor_id=bill.vendor_id,
                vendor_name=bill.vendor.name if bill.vendor else None,
                total_amount=bill.total_amount,
                invoice_date=bill.invoice_date,
                created_at=str(bill.created_at) if bill.created_at else None,
                match_score=1.0,
                match_reasons=["Exact match: vendor + invoice number + amount"],
            ))
        
        return matches
    
    async def _find_vendor_invoice_matches(
        self,
        db: AsyncSession,
        vendor_id: UUID,
        invoice_number: str,
        exclude_bill_id: Optional[UUID],
        Bill,
        BillStatus,
    ) -> List[DuplicateMatch]:
        """Find vendor + invoice number matches."""
        matches = []
        
        query = (
            select(Bill)
            .options(selectinload(Bill.vendor))
            .where(
                and_(
                    Bill.vendor_id == vendor_id,
                    Bill.invoice_number == invoice_number,
                    Bill.status.not_in([BillStatus.FAILED, BillStatus.DUPLICATE]),
                )
            )
        )
        
        if exclude_bill_id:
            query = query.where(Bill.id != exclude_bill_id)
        
        result = await db.execute(query)
        bills = result.scalars().all()
        
        for bill in bills:
            matches.append(DuplicateMatch(
                bill_id=bill.id,
                invoice_number=bill.invoice_number,
                vendor_id=bill.vendor_id,
                vendor_name=bill.vendor.name if bill.vendor else None,
                total_amount=bill.total_amount,
                invoice_date=bill.invoice_date,
                created_at=str(bill.created_at) if bill.created_at else None,
                match_score=0.85,
                match_reasons=["Match: vendor + invoice number"],
            ))
        
        return matches
    
    async def _find_vendor_amount_matches(
        self,
        db: AsyncSession,
        vendor_id: UUID,
        total_amount: Decimal,
        invoice_date: date,
        exclude_bill_id: Optional[UUID],
        Bill,
        BillStatus,
    ) -> List[DuplicateMatch]:
        """Find vendor + amount matches within date range."""
        matches = []
        
        date_from = invoice_date - timedelta(days=self.DATE_RANGE_DAYS)
        date_to = invoice_date + timedelta(days=self.DATE_RANGE_DAYS)
        
        query = (
            select(Bill)
            .options(selectinload(Bill.vendor))
            .where(
                and_(
                    Bill.vendor_id == vendor_id,
                    Bill.total_amount >= total_amount - self.AMOUNT_TOLERANCE,
                    Bill.total_amount <= total_amount + self.AMOUNT_TOLERANCE,
                    Bill.invoice_date >= date_from,
                    Bill.invoice_date <= date_to,
                    Bill.status.not_in([BillStatus.FAILED, BillStatus.DUPLICATE]),
                )
            )
        )
        
        if exclude_bill_id:
            query = query.where(Bill.id != exclude_bill_id)
        
        result = await db.execute(query)
        bills = result.scalars().all()
        
        for bill in bills:
            matches.append(DuplicateMatch(
                bill_id=bill.id,
                invoice_number=bill.invoice_number,
                vendor_id=bill.vendor_id,
                vendor_name=bill.vendor.name if bill.vendor else None,
                total_amount=bill.total_amount,
                invoice_date=bill.invoice_date,
                created_at=str(bill.created_at) if bill.created_at else None,
                match_score=0.6,
                match_reasons=[f"Match: vendor + amount (within {self.DATE_RANGE_DAYS} days)"],
            ))
        
        return matches
    
    async def _find_invoice_amount_matches(
        self,
        db: AsyncSession,
        invoice_number: str,
        total_amount: Decimal,
        exclude_bill_id: Optional[UUID],
        Bill,
        BillStatus,
    ) -> List[DuplicateMatch]:
        """Find invoice number + amount matches."""
        matches = []
        
        query = (
            select(Bill)
            .options(selectinload(Bill.vendor))
            .where(
                and_(
                    Bill.invoice_number == invoice_number,
                    Bill.total_amount >= total_amount - self.AMOUNT_TOLERANCE,
                    Bill.total_amount <= total_amount + self.AMOUNT_TOLERANCE,
                    Bill.status.not_in([BillStatus.FAILED, BillStatus.DUPLICATE]),
                )
            )
        )
        
        if exclude_bill_id:
            query = query.where(Bill.id != exclude_bill_id)
        
        result = await db.execute(query)
        bills = result.scalars().all()
        
        for bill in bills:
            matches.append(DuplicateMatch(
                bill_id=bill.id,
                invoice_number=bill.invoice_number,
                vendor_id=bill.vendor_id,
                vendor_name=bill.vendor.name if bill.vendor else None,
                total_amount=bill.total_amount,
                invoice_date=bill.invoice_date,
                created_at=str(bill.created_at) if bill.created_at else None,
                match_score=0.5,
                match_reasons=["Match: invoice number + amount"],
            ))
        
        return matches
    
    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        """Safely convert a value to Decimal."""
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        try:
            if isinstance(value, float):
                return Decimal(str(value))
            return Decimal(str(value))
        except Exception:
            return None
    
    def _to_date(self, value: Any) -> Optional[date]:
        """Safely convert a value to date."""
        if value is None:
            return None
        if isinstance(value, date):
            return value
        try:
            from datetime import datetime
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, str):
                return date.fromisoformat(value)
        except Exception:
            return None
        return None
