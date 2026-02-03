"""
BillAgent Pro - Bill Processing Service
=========================================
Orchestrates the full bill processing pipeline:
1. Digitizer Agent → OCR extraction
2. Auditor Agent → Validation
3. Controller Agent → Duplicate detection
4. Accountant Agent → GL code assignment

This service chains all agents and manages the workflow.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ProcessingStage(str, Enum):
    """Stages of bill processing."""
    DIGITIZATION = "digitization"
    VALIDATION = "validation"
    DUPLICATE_CHECK = "duplicate_check"
    GL_ASSIGNMENT = "gl_assignment"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessingStepResult:
    """Result of a single processing step."""
    stage: ProcessingStage
    success: bool
    duration_ms: int
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    data: Optional[Dict[str, Any]] = None
    message: str = ""


@dataclass
class ProcessingResult:
    """Overall result of bill processing."""
    bill_id: Optional[UUID] = None
    status: str = "PROCESSING"
    stages_completed: List[str] = field(default_factory=list)
    stage_results: List[ProcessingStepResult] = field(default_factory=list)
    total_processing_time_ms: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "bill_id": str(self.bill_id) if self.bill_id else None,
            "status": self.status,
            "stages_completed": self.stages_completed,
            "total_processing_time_ms": self.total_processing_time_ms,
            "errors": self.errors,
            "warnings": self.warnings,
            "stage_results": [
                {
                    "stage": r.stage.value,
                    "success": r.success,
                    "duration_ms": r.duration_ms,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "message": r.message,
                }
                for r in self.stage_results
            ],
        }


class BillProcessingService:
    """
    Orchestrates the complete bill processing pipeline.
    
    Pipeline Flow:
    1. Digitizer.extract() → OCR extraction from image
    2. Save to DB with status=PROCESSING
    3. Auditor.validate() → Math and business rule validation
    4. Controller.check_duplicate() → Duplicate detection
    5. Accountant.assign_gl_codes() → Expense categorization
    6. Update status (APPROVED/NEEDS_REVIEW/DUPLICATE)
    7. Log to audit_logs
    
    Each step logs to audit_logs for traceability.
    """
    
    def __init__(
        self,
        digitizer=None,
        auditor=None,
        controller=None,
        accountant=None,
        bill_repository=None,
        vendor_repository=None,
    ):
        """
        Initialize the Bill Processing Service.
        
        All agents can be dependency-injected for testing.
        If not provided, they will be created with defaults.
        """
        # Lazy import to avoid circular dependencies
        self.digitizer = digitizer
        self.auditor = auditor
        self.controller = controller
        self.accountant = accountant
        self.bill_repository = bill_repository
        self.vendor_repository = vendor_repository
        
        logger.info("BillProcessingService initialized")
    
    def _ensure_agents_initialized(self):
        """Ensure all agents are initialized."""
        if self.digitizer is None:
            from agents.digitizer import DigitizerAgent
            self.digitizer = DigitizerAgent()
        
        if self.auditor is None:
            from agents.auditor import AuditorAgent
            self.auditor = AuditorAgent()
        
        if self.controller is None:
            from agents.controller import ControllerAgent
            self.controller = ControllerAgent()
        
        if self.accountant is None:
            from agents.accountant import AccountantAgent
            self.accountant = AccountantAgent()
    
    async def process_bill(
        self,
        image_bytes: bytes,
        image_url: str,
        db: AsyncSession,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> ProcessingResult:
        """
        Process a bill image through the complete pipeline.
        
        Args:
            image_bytes: Raw image bytes (JPEG, PNG, etc.)
            image_url: Path/URL where the image is stored
            db: AsyncSession for database operations
            user_id: User who uploaded the bill (optional)
            task_id: Celery task ID (optional)
        
        Returns:
            ProcessingResult with bill_id, status, and stage results
        """
        from app.models import Bill, LineItem, AuditLog, Vendor
        from app.models.bill import BillStatus
        from app.repositories.bill_repository import BillRepository
        from app.repositories.vendor_repository import VendorRepository
        
        self._ensure_agents_initialized()
        
        start_time = time.perf_counter()
        result = ProcessingResult()
        
        # Initialize repositories if not provided
        bill_repo = self.bill_repository or BillRepository(db)
        vendor_repo = self.vendor_repository or VendorRepository(db)
        
        bill: Optional[Bill] = None
        
        try:
            # =================================================================
            # Stage 1: DIGITIZATION
            # =================================================================
            stage_start = time.perf_counter()
            logger.info("Stage 1: Starting digitization...")
            
            digitization_result = await self.digitizer.extract(
                image_bytes=image_bytes,
                image_url=image_url,
                db_session=db,
            )
            
            stage_duration = int((time.perf_counter() - stage_start) * 1000)
            
            if digitization_result.status.value == "failed":
                result.stage_results.append(ProcessingStepResult(
                    stage=ProcessingStage.DIGITIZATION,
                    success=False,
                    duration_ms=stage_duration,
                    errors=digitization_result.validation_errors,
                    message="Digitization failed",
                ))
                result.status = "FAILED"
                result.errors = digitization_result.validation_errors
                return result
            
            result.stage_results.append(ProcessingStepResult(
                stage=ProcessingStage.DIGITIZATION,
                success=True,
                duration_ms=stage_duration,
                data=digitization_result.to_dict(),
                message=f"OCR completed with {digitization_result.ocr_result.overall_confidence:.1%} confidence",
            ))
            result.stages_completed.append("digitization")
            
            # =================================================================
            # Save Bill to Database (status=PROCESSING)
            # =================================================================
            bill_data = digitization_result.bill_data
            
            # Create Bill entity
            bill = Bill(
                vendor_id=digitization_result.vendor_id,
                invoice_number=bill_data.get("invoice_number"),
                invoice_date=bill_data.get("invoice_date"),
                due_date=bill_data.get("due_date"),
                subtotal=self._to_decimal(bill_data.get("subtotal")),
                tax_amount=self._to_decimal(bill_data.get("tax_amount")) or Decimal("0.00"),
                total_amount=self._to_decimal(bill_data.get("total_amount")),
                currency=bill_data.get("currency", "INR"),
                status=BillStatus.PROCESSING,
                confidence_score=digitization_result.ocr_result.overall_confidence if digitization_result.ocr_result else None,
                field_confidence=digitization_result.metadata.get("field_confidence") if digitization_result.metadata else None,
                image_url=image_url,
                bounding_boxes=digitization_result.metadata.get("bounding_boxes") if digitization_result.metadata else None,
                task_id=task_id,
                processing_time_ms=stage_duration,
                ocr_engine=digitization_result.ocr_result.engine_used.value if digitization_result.ocr_result else None,
            )
            
            # Add line items
            line_items_data = bill_data.get("line_items", [])
            for idx, item_data in enumerate(line_items_data):
                line_item = LineItem(
                    description=item_data.get("description", f"Item {idx + 1}"),
                    quantity=self._to_decimal(item_data.get("quantity")) or Decimal("1"),
                    unit=item_data.get("unit"),
                    unit_price=self._to_decimal(item_data.get("unit_price")) or Decimal("0"),
                    total_price=self._to_decimal(item_data.get("total_price")) or Decimal("0"),
                    tax_amount=self._to_decimal(item_data.get("tax_amount")),
                    gl_code=item_data.get("gl_code"),
                    confidence_score=item_data.get("confidence_score"),
                    field_confidence=item_data.get("field_confidence"),
                    bounding_box=item_data.get("bounding_box"),
                    sort_order=idx,
                )
                bill.line_items.append(line_item)
            
            # Save bill
            bill = await bill_repo.create(bill)
            result.bill_id = bill.id
            
            # Create audit log
            await self._create_audit_log(
                db=db,
                bill_id=bill.id,
                action="CREATED",
                agent_name="Digitizer",
                description=f"Bill created from OCR extraction",
            )
            
            logger.info(f"Bill created with ID: {bill.id}")
            
            # =================================================================
            # Stage 2: VALIDATION (Auditor Agent)
            # =================================================================
            stage_start = time.perf_counter()
            logger.info(f"Stage 2: Validating bill {bill.id}...")
            
            # Prepare data for validation
            validation_data = {
                "subtotal": bill.subtotal,
                "tax_amount": bill.tax_amount,
                "total_amount": bill.total_amount,
                "invoice_date": bill.invoice_date,
                "due_date": bill.due_date,
                "line_items": [
                    {
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "total_price": item.total_price,
                    }
                    for item in bill.line_items
                ],
            }
            
            validation_result = self.auditor.validate(validation_data)
            
            stage_duration = int((time.perf_counter() - stage_start) * 1000)
            
            result.stage_results.append(ProcessingStepResult(
                stage=ProcessingStage.VALIDATION,
                success=validation_result.is_valid,
                duration_ms=stage_duration,
                errors=[e.to_dict() for e in validation_result.errors],
                warnings=[w.to_dict() for w in validation_result.warnings],
                data=validation_result.to_dict(),
                message=f"Validation: {len(validation_result.errors)} errors, {len(validation_result.warnings)} warnings",
            ))
            result.stages_completed.append("validation")
            
            # Store validation errors on bill
            if validation_result.errors or validation_result.warnings:
                bill.validation_errors = [e.to_dict() for e in validation_result.errors + validation_result.warnings]
                result.errors.extend([e.to_dict() for e in validation_result.errors])
                result.warnings.extend([w.to_dict() for w in validation_result.warnings])
                
                # Mark line items with math errors
                for error in validation_result.errors:
                    if error.rule == "RULE_4_LINE_ITEM_MATH" and "line_items[" in error.field:
                        # Extract index from field name like "line_items[0].total_price"
                        try:
                            idx = int(error.field.split("[")[1].split("]")[0])
                            if 0 <= idx < len(bill.line_items):
                                bill.line_items[idx].has_math_error = True
                        except (ValueError, IndexError):
                            pass
            
            # Create audit log for validation
            await self._create_audit_log(
                db=db,
                bill_id=bill.id,
                action="VALIDATED",
                agent_name="Auditor",
                description=f"Validation: {len(validation_result.errors)} errors, {len(validation_result.warnings)} warnings",
                new_value={"validation_result": validation_result.to_dict()},
            )
            
            # =================================================================
            # Stage 3: DUPLICATE CHECK (Controller Agent)
            # =================================================================
            stage_start = time.perf_counter()
            logger.info(f"Stage 3: Checking for duplicates...")
            
            duplicate_data = {
                "vendor_id": bill.vendor_id,
                "invoice_number": bill.invoice_number,
                "total_amount": bill.total_amount,
                "invoice_date": bill.invoice_date,
            }
            
            duplicate_result = await self.controller.check_duplicate(
                bill_data=duplicate_data,
                db=db,
                exclude_bill_id=bill.id,  # Exclude current bill
            )
            
            stage_duration = int((time.perf_counter() - stage_start) * 1000)
            
            result.stage_results.append(ProcessingStepResult(
                stage=ProcessingStage.DUPLICATE_CHECK,
                success=not duplicate_result.is_duplicate,
                duration_ms=stage_duration,
                data=duplicate_result.to_dict(),
                message=duplicate_result.message,
            ))
            result.stages_completed.append("duplicate_check")
            
            # Update bill if duplicate found
            if duplicate_result.is_duplicate and duplicate_result.potential_duplicates:
                bill.is_duplicate = True
                bill.duplicate_of_id = duplicate_result.potential_duplicates[0].bill_id
            
            # Create audit log
            await self._create_audit_log(
                db=db,
                bill_id=bill.id,
                action="DUPLICATE_CHECK",
                agent_name="Controller",
                description=duplicate_result.message,
                new_value={"duplicate_result": duplicate_result.to_dict()},
            )
            
            # =================================================================
            # Stage 4: GL CODE ASSIGNMENT (Accountant Agent)
            # =================================================================
            stage_start = time.perf_counter()
            logger.info(f"Stage 4: Assigning GL codes...")
            
            line_items_for_gl = [
                {
                    "description": item.description,
                    "gl_code": item.gl_code,
                }
                for item in bill.line_items
            ]
            
            gl_result = await self.accountant.assign_gl_codes(
                line_items=line_items_for_gl,
                vendor_id=bill.vendor_id,
                db=db,
            )
            
            stage_duration = int((time.perf_counter() - stage_start) * 1000)
            
            # Update line items with GL codes
            for assignment in gl_result.assignments:
                idx = assignment.line_item_index
                if 0 <= idx < len(bill.line_items):
                    bill.line_items[idx].gl_code = assignment.gl_code
                    bill.line_items[idx].gl_code_source = assignment.source.value
            
            result.stage_results.append(ProcessingStepResult(
                stage=ProcessingStage.GL_ASSIGNMENT,
                success=True,
                duration_ms=stage_duration,
                data=gl_result.to_dict(),
                message=f"GL codes assigned: {gl_result.assigned_count}/{gl_result.total_items}",
            ))
            result.stages_completed.append("gl_assignment")
            
            # Create audit log
            await self._create_audit_log(
                db=db,
                bill_id=bill.id,
                action="GL_ASSIGNED",
                agent_name="Accountant",
                description=f"GL codes assigned: {gl_result.assigned_count}/{gl_result.total_items}",
                new_value={"gl_result": gl_result.to_dict()},
            )
            
            # =================================================================
            # Determine Final Status
            # =================================================================
            if duplicate_result.is_duplicate:
                final_status = BillStatus.DUPLICATE
            elif not validation_result.is_valid:
                final_status = BillStatus.NEEDS_REVIEW
            elif validation_result.has_warnings:
                # Warnings don't block approval, but we might want review
                if bill.confidence_score and bill.confidence_score < 0.85:
                    final_status = BillStatus.NEEDS_REVIEW
                else:
                    final_status = BillStatus.APPROVED
            else:
                final_status = BillStatus.APPROVED
            
            bill.status = final_status
            
            # Update processing time
            total_time_ms = int((time.perf_counter() - start_time) * 1000)
            bill.processing_time_ms = total_time_ms
            
            # Save final state
            await bill_repo.update(bill)
            
            # Final audit log
            await self._create_audit_log(
                db=db,
                bill_id=bill.id,
                action="PROCESSING_COMPLETE",
                agent_name="BillProcessingService",
                description=f"Processing complete with status: {final_status.value}",
                new_value={"status": final_status.value},
            )
            
            result.status = final_status.value
            result.stages_completed.append("completed")
            result.total_processing_time_ms = total_time_ms
            
            logger.info(
                f"Bill {bill.id} processing complete: status={final_status.value}, "
                f"time={total_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Bill processing failed: {e}", exc_info=True)
            
            # Update bill status to FAILED if it exists
            if bill:
                bill.status = BillStatus.FAILED
                await bill_repo.update(bill)
                
                await self._create_audit_log(
                    db=db,
                    bill_id=bill.id,
                    action="PROCESSING_FAILED",
                    agent_name="BillProcessingService",
                    description=f"Processing failed: {str(e)}",
                )
            
            result.status = "FAILED"
            result.errors.append({
                "field": "processing",
                "message": str(e),
                "severity": "error",
            })
            
            return result
    
    async def _create_audit_log(
        self,
        db: AsyncSession,
        bill_id: UUID,
        action: str,
        agent_name: str,
        description: str,
        field_name: Optional[str] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
    ):
        """Create an audit log entry."""
        from app.models import AuditLog
        
        try:
            audit_log = AuditLog(
                bill_id=bill_id,
                action=action,
                agent_name=agent_name,
                description=description,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
            )
            db.add(audit_log)
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to create audit log: {e}")
    
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
    
    async def reprocess_bill(
        self,
        bill_id: UUID,
        db: AsyncSession,
        skip_digitization: bool = True,
    ) -> ProcessingResult:
        """
        Reprocess an existing bill through validation, duplicate check, and GL assignment.
        
        Useful for re-running validation after manual corrections.
        
        Args:
            bill_id: Bill UUID to reprocess
            db: AsyncSession for database operations
            skip_digitization: If True, skip OCR and use existing data
        
        Returns:
            ProcessingResult with updated status and stage results
        """
        from app.models import Bill
        from app.models.bill import BillStatus
        from app.repositories.bill_repository import BillRepository
        
        self._ensure_agents_initialized()
        
        bill_repo = self.bill_repository or BillRepository(db)
        
        # Get existing bill
        bill = await bill_repo.get_by_id(bill_id)
        if not bill:
            return ProcessingResult(
                status="FAILED",
                errors=[{"field": "bill_id", "message": "Bill not found", "severity": "error"}],
            )
        
        start_time = time.perf_counter()
        result = ProcessingResult(bill_id=bill_id)
        
        # Reset bill status
        bill.status = BillStatus.PROCESSING
        bill.is_duplicate = False
        bill.duplicate_of_id = None
        bill.validation_errors = None
        await bill_repo.update(bill)
        
        # Run validation, duplicate check, and GL assignment
        # (Same logic as process_bill stages 2-4)
        
        # Stage 2: Validation
        stage_start = time.perf_counter()
        validation_data = {
            "subtotal": bill.subtotal,
            "tax_amount": bill.tax_amount,
            "total_amount": bill.total_amount,
            "invoice_date": bill.invoice_date,
            "due_date": bill.due_date,
            "line_items": [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                }
                for item in bill.line_items
            ],
        }
        
        validation_result = self.auditor.validate(validation_data)
        stage_duration = int((time.perf_counter() - stage_start) * 1000)
        
        result.stage_results.append(ProcessingStepResult(
            stage=ProcessingStage.VALIDATION,
            success=validation_result.is_valid,
            duration_ms=stage_duration,
            errors=[e.to_dict() for e in validation_result.errors],
            warnings=[w.to_dict() for w in validation_result.warnings],
            message=f"Validation: {len(validation_result.errors)} errors",
        ))
        result.stages_completed.append("validation")
        
        if validation_result.errors or validation_result.warnings:
            bill.validation_errors = [e.to_dict() for e in validation_result.errors + validation_result.warnings]
            result.errors.extend([e.to_dict() for e in validation_result.errors])
            result.warnings.extend([w.to_dict() for w in validation_result.warnings])
        
        # Stage 3: Duplicate Check
        stage_start = time.perf_counter()
        duplicate_data = {
            "vendor_id": bill.vendor_id,
            "invoice_number": bill.invoice_number,
            "total_amount": bill.total_amount,
            "invoice_date": bill.invoice_date,
        }
        
        duplicate_result = await self.controller.check_duplicate(
            bill_data=duplicate_data,
            db=db,
            exclude_bill_id=bill.id,
        )
        stage_duration = int((time.perf_counter() - stage_start) * 1000)
        
        result.stage_results.append(ProcessingStepResult(
            stage=ProcessingStage.DUPLICATE_CHECK,
            success=not duplicate_result.is_duplicate,
            duration_ms=stage_duration,
            message=duplicate_result.message,
        ))
        result.stages_completed.append("duplicate_check")
        
        if duplicate_result.is_duplicate and duplicate_result.potential_duplicates:
            bill.is_duplicate = True
            bill.duplicate_of_id = duplicate_result.potential_duplicates[0].bill_id
        
        # Stage 4: GL Assignment
        stage_start = time.perf_counter()
        line_items_for_gl = [
            {"description": item.description, "gl_code": item.gl_code}
            for item in bill.line_items
        ]
        
        gl_result = await self.accountant.assign_gl_codes(
            line_items=line_items_for_gl,
            vendor_id=bill.vendor_id,
            db=db,
        )
        stage_duration = int((time.perf_counter() - stage_start) * 1000)
        
        for assignment in gl_result.assignments:
            idx = assignment.line_item_index
            if 0 <= idx < len(bill.line_items):
                bill.line_items[idx].gl_code = assignment.gl_code
                bill.line_items[idx].gl_code_source = assignment.source.value
        
        result.stage_results.append(ProcessingStepResult(
            stage=ProcessingStage.GL_ASSIGNMENT,
            success=True,
            duration_ms=stage_duration,
            message=f"GL codes: {gl_result.assigned_count}/{gl_result.total_items}",
        ))
        result.stages_completed.append("gl_assignment")
        
        # Determine final status
        if duplicate_result.is_duplicate:
            final_status = BillStatus.DUPLICATE
        elif not validation_result.is_valid:
            final_status = BillStatus.NEEDS_REVIEW
        else:
            final_status = BillStatus.APPROVED
        
        bill.status = final_status
        bill.processing_time_ms = int((time.perf_counter() - start_time) * 1000)
        
        await bill_repo.update(bill)
        
        result.status = final_status.value
        result.stages_completed.append("completed")
        result.total_processing_time_ms = bill.processing_time_ms
        
        return result
