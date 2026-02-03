"""
BillAgent Pro - FastAPI Application
====================================
Production-ready API with PostgreSQL, async support, and comprehensive endpoints.
Includes Celery integration for async bill processing.
"""

import base64
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import redis

# Internal app modules
from .config import settings
from .database import get_db, init_db, close_db
from .models import Bill, LineItem, Vendor, AuditLog, GLCode, User
from .models.bill import BillStatus
from .schemas import (
    BillUploadResponse, BillStatusResponse, BillRead, BillUpdate, BillList, BillSummary,
    VendorRead, VendorCreate, VendorList,
    TaskStatus, HealthCheck, ErrorResponse, PaginatedResponse,
    AuditLogList, AuditLogRead
)
from .schemas.gl_code_schema import GLCodeRead, GLCodeList

# Auth imports
from .api.v1.auth import router as auth_router, get_current_active_user
from .api.v1.users import router as users_router
from .api.v1.permissions import Permission, require_permission
from .middleware.security import setup_security

# Celery imports (lazy loaded for health checks)
try:
    from celery_app import celery_app, TaskProgress, REDIS_URL
    from tasks.process_bill import process_bill_task, get_task_status, cancel_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    celery_app = None
    TaskProgress = None
    REDIS_URL = settings.redis_url

# =============================================================================
# Application Lifespan
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    print(f"🚀 Starting BillAgent Pro v{settings.api_version}")
    print(f"   Environment: {settings.environment}")
    try:
        await init_db()
        print("   ✅ Database connected")
    except Exception as e:
        print(f"   ⚠️  Database connection failed: {e}")
        print("   ⚠️  API will run without database (some features unavailable)")
    yield
    # Shutdown
    print("🔌 Shutting down BillAgent Pro...")
    try:
        await close_db()
        print("   ✅ Database connections closed")
    except Exception:
        pass


# =============================================================================
# Sentry Integration (Error Monitoring)
# =============================================================================
if settings.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1 if settings.environment == "production" else 1.0,
            profiles_sample_rate=0.1,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
        )
        print("   ✅ Sentry error monitoring enabled")
    except ImportError:
        print("   ⚠️ Sentry SDK not installed, skipping error monitoring")


# =============================================================================
# FastAPI Application
# =============================================================================
app = FastAPI(
    title="BillAgent Pro API",
    description="AI-Powered Bill Processing & Management System",
    version=settings.api_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS Middleware - More restrictive in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.environment != "development" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# Security Middleware (rate limiting, security headers, etc.)
setup_security(
    app,
    rate_limit_per_minute=settings.rate_limit_per_minute,
    enable_rate_limiting=settings.environment != "development",  # Disable in dev
    enable_security_headers=True,
    enable_request_validation=True,
    enable_request_id=True
)

# Include auth routers
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(users_router, prefix=settings.api_v1_prefix)


# =============================================================================
# Exception Handlers
# =============================================================================
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=f"HTTP_{exc.status_code}",
            message=exc.detail,
            timestamp=datetime.utcnow()
        ).model_dump(mode="json")
    )


# =============================================================================
# Health Check Endpoints
# =============================================================================
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint."""
    return {"message": "BillAgent Pro API", "version": settings.api_version}


@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check API health status."""
    # Test database connection
    try:
        await db.execute(select(func.now()))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    # Test Redis connection
    redis_status = "not_configured"
    try:
        r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        if r.ping():
            redis_status = "connected"
        r.close()
    except Exception:
        redis_status = "disconnected"
    
    # Test Celery workers (check if any workers are available)
    celery_status = "not_configured"
    if CELERY_AVAILABLE and celery_app:
        try:
            # Check if there are active workers
            inspect = celery_app.control.inspect(timeout=1)
            workers = inspect.ping()
            if workers:
                celery_status = f"connected ({len(workers)} workers)"
            else:
                celery_status = "no_workers"
        except Exception:
            celery_status = "unavailable"
    
    return HealthCheck(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.api_version,
        environment=settings.environment,
        database=db_status,
        redis=redis_status,
        celery=celery_status,
        timestamp=datetime.utcnow()
    )


# =============================================================================
# Bill Endpoints
# =============================================================================
@app.post(
    "/api/v1/bills/upload",
    response_model=BillUploadResponse,
    tags=["Bills"],
    summary="Upload a bill for async processing"
)
async def upload_bill(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a bill image for OCR processing.
    
    Returns a task_id that can be used to poll for status.
    The bill is processed asynchronously using Celery workers.
    
    Workflow:
    1. Validate file type and size
    2. Create initial bill record with PROCESSING status
    3. Dispatch Celery task for async processing
    4. Return task_id for status polling
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Validate file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    # Save the image path (in production, upload to blob storage)
    image_filename = f"bills/{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid.uuid4()}_{file.filename}"
    # TODO: Save to Azure Blob Storage or local filesystem
    
    # Check if Celery is available
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Async processing not available. Celery workers are not configured."
        )
    
    # Dispatch Celery task
    try:
        # Encode image as base64 for task
        image_bytes_b64 = base64.b64encode(content).decode("utf-8")
        
        # Dispatch async task
        result = process_bill_task.delay(
            image_bytes_b64=image_bytes_b64,
            image_url=image_filename,
            user_id=None,  # TODO: Get from auth context
            metadata={
                "filename": file.filename,
                "content_type": file.content_type,
                "size": len(content),
            }
        )
        
        task_id = result.id
        
        # Initialize progress tracking
        if TaskProgress:
            progress = TaskProgress(task_id)
            progress.update(
                stage="queued",
                percent=0,
                message="Bill queued for processing",
                data={"filename": file.filename}
            )
        
        # Create audit log
        audit_log = AuditLog(
            action="BILL_UPLOADED",
            agent_name="API",
            description=f"Bill upload initiated: {file.filename}",
            new_value={"filename": file.filename, "size": len(content), "task_id": task_id}
        )
        db.add(audit_log)
        await db.commit()
        
        return BillUploadResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Bill uploaded successfully. Processing started.",
            estimated_time_seconds=30  # Estimate based on typical processing time
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start bill processing: {str(e)}"
        )


@app.get(
    "/api/v1/bills/status/{task_id}",
    response_model=BillStatusResponse,
    tags=["Bills"],
    summary="Check bill processing status"
)
async def get_bill_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the processing status of a bill by task ID.
    
    Poll this endpoint after upload to check progress.
    Returns detailed progress information from Celery/Redis.
    """
    if not CELERY_AVAILABLE:
        # Fallback: Look up by task_id in database
        result = await db.execute(
            select(Bill).where(Bill.task_id == task_id)
        )
        bill = result.scalar_one_or_none()
        
        if not bill:
            raise HTTPException(status_code=404, detail="Task not found")
        
        status_map = {
            BillStatus.PROCESSING: TaskStatus.PROCESSING,
            BillStatus.NEEDS_REVIEW: TaskStatus.COMPLETED,
            BillStatus.APPROVED: TaskStatus.COMPLETED,
            BillStatus.POSTED: TaskStatus.COMPLETED,
            BillStatus.FAILED: TaskStatus.FAILED,
            BillStatus.DUPLICATE: TaskStatus.COMPLETED,
        }
        
        return BillStatusResponse(
            task_id=task_id,
            status=status_map.get(bill.status, TaskStatus.PROCESSING),
            progress=1.0 if bill.status != BillStatus.PROCESSING else 0.5,
            current_step="Complete" if bill.status != BillStatus.PROCESSING else "Processing",
            bill_id=bill.id if bill.status != BillStatus.PROCESSING else None,
            error=str(bill.validation_errors) if bill.status == BillStatus.FAILED else None,
            redirect_url=f"/api/v1/bills/{bill.id}" if bill.status != BillStatus.PROCESSING else None
        )
    
    # Get status from Celery/Redis
    task_status = get_task_status(task_id)
    
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Map Celery status to TaskStatus enum
    celery_status = task_status.get("celery_status", "PENDING")
    status_mapping = {
        "PENDING": TaskStatus.PENDING,
        "STARTED": TaskStatus.PROCESSING,
        "SUCCESS": TaskStatus.COMPLETED,
        "FAILURE": TaskStatus.FAILED,
        "RETRY": TaskStatus.PROCESSING,
        "REVOKED": TaskStatus.FAILED,
    }
    
    api_status = status_mapping.get(celery_status, TaskStatus.PROCESSING)
    
    # Override with Redis progress status if available
    redis_status = task_status.get("status", "").lower()
    if redis_status == "completed":
        api_status = TaskStatus.COMPLETED
    elif redis_status == "failed":
        api_status = TaskStatus.FAILED
    elif redis_status == "processing":
        api_status = TaskStatus.PROCESSING
    
    # Get bill_id if completed
    bill_id = task_status.get("bill_id")
    if bill_id:
        try:
            bill_id = uuid.UUID(bill_id)
        except ValueError:
            bill_id = None
    
    return BillStatusResponse(
        task_id=task_id,
        status=api_status,
        progress=task_status.get("percent", 0) / 100.0,
        current_step=task_status.get("stage", "unknown"),
        bill_id=bill_id,
        error=task_status.get("error"),
        redirect_url=f"/api/v1/bills/{bill_id}" if bill_id and api_status == TaskStatus.COMPLETED else None
    )


@app.delete(
    "/api/v1/bills/status/{task_id}",
    tags=["Bills"],
    summary="Cancel a pending bill processing task"
)
async def cancel_bill_processing(
    task_id: str,
):
    """
    Cancel a pending or running bill processing task.
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Async processing not available"
        )
    
    try:
        cancel_task(task_id)
        return {"message": "Task cancellation requested", "task_id": task_id}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


@app.get(
    "/api/v1/bills/{bill_id}",
    response_model=BillRead,
    tags=["Bills"],
    summary="Get bill details"
)
async def get_bill(
    bill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get full details of a bill including line items.
    """
    result = await db.execute(
        select(Bill)
        .options(selectinload(Bill.line_items), selectinload(Bill.vendor))
        .where(Bill.id == bill_id)
    )
    bill = result.scalar_one_or_none()
    
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    return bill


@app.patch(
    "/api/v1/bills/{bill_id}",
    response_model=BillRead,
    tags=["Bills"],
    summary="Update bill fields"
)
async def update_bill(
    bill_id: uuid.UUID,
    update: BillUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update bill fields (for corrections and approval).
    """
    result = await db.execute(
        select(Bill)
        .options(selectinload(Bill.line_items))
        .where(Bill.id == bill_id)
    )
    bill = result.scalar_one_or_none()
    
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Track old values for audit
    old_values = {}
    new_values = {}
    
    # Update fields
    update_data = update.model_dump(exclude_unset=True, exclude={"line_items"})
    for field, value in update_data.items():
        if hasattr(bill, field):
            old_value = getattr(bill, field)
            if old_value != value:
                old_values[field] = str(old_value) if old_value else None
                new_values[field] = str(value) if value else None
                setattr(bill, field, value)
    
    bill.updated_at = datetime.utcnow()
    
    # Create audit log for changes
    if old_values:
        audit_log = AuditLog(
            bill_id=bill.id,
            action="UPDATED",
            agent_name="API",
            description="Bill fields updated",
            old_value=old_values,
            new_value=new_values
        )
        db.add(audit_log)
    
    await db.commit()
    await db.refresh(bill)
    
    return bill


@app.get(
    "/api/v1/bills",
    response_model=BillList,
    tags=["Bills"],
    summary="List all bills"
)
async def list_bills(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[BillStatus] = Query(None, description="Filter by status"),
    vendor_id: Optional[uuid.UUID] = Query(None, description="Filter by vendor"),
    search: Optional[str] = Query(None, description="Search invoice number"),
    db: AsyncSession = Depends(get_db)
):
    """
    List bills with pagination and filtering.
    """
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
        filters.append(Bill.invoice_number.ilike(f"%{search}%"))
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Bill.created_at.desc()).offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    bills = result.scalars().all()
    
    # Convert to summary format
    items = []
    for bill in bills:
        items.append(BillSummary(
            id=bill.id,
            vendor_name=bill.vendor.name if bill.vendor else None,
            invoice_number=bill.invoice_number,
            invoice_date=bill.invoice_date,
            total_amount=bill.total_amount,
            status=bill.status,
            confidence_score=bill.confidence_score,
            has_errors=bool(bill.validation_errors),
            created_at=bill.created_at
        ))
    
    return BillList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@app.post(
    "/api/v1/bills/{bill_id}/approve",
    response_model=BillRead,
    tags=["Bills"],
    summary="Approve a bill"
)
async def approve_bill(
    bill_id: uuid.UUID,
    approved_by: str = Query(..., description="Approver name/email"),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a bill after review.
    """
    result = await db.execute(select(Bill).where(Bill.id == bill_id))
    bill = result.scalar_one_or_none()
    
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    if bill.status not in (BillStatus.NEEDS_REVIEW, BillStatus.DUPLICATE):
        raise HTTPException(
            status_code=400,
            detail=f"Bill cannot be approved in status: {bill.status}"
        )
    
    old_status = bill.status
    bill.status = BillStatus.APPROVED
    bill.approved_by = approved_by
    bill.approved_at = datetime.utcnow()
    bill.updated_at = datetime.utcnow()
    
    # Audit log
    audit_log = AuditLog(
        bill_id=bill.id,
        action="APPROVED",
        agent_name="API",
        description=f"Bill approved by {approved_by}",
        old_value={"status": old_status.value},
        new_value={"status": BillStatus.APPROVED.value, "approved_by": approved_by},
        user_email=approved_by
    )
    db.add(audit_log)
    
    await db.commit()
    await db.refresh(bill)
    
    return bill


# =============================================================================
# Vendor Endpoints
# =============================================================================
@app.get(
    "/api/v1/vendors",
    response_model=VendorList,
    tags=["Vendors"],
    summary="List all vendors"
)
async def list_vendors(
    search: Optional[str] = Query(None, description="Search vendor name"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all vendors.
    """
    query = select(Vendor)
    if search:
        query = query.where(Vendor.name.ilike(f"%{search}%"))
    
    query = query.order_by(Vendor.name)
    result = await db.execute(query)
    vendors = result.scalars().all()
    
    return VendorList(
        items=[VendorRead.model_validate(v) for v in vendors],
        total=len(vendors)
    )


@app.post(
    "/api/v1/vendors",
    response_model=VendorRead,
    tags=["Vendors"],
    summary="Create a vendor"
)
async def create_vendor(
    vendor: VendorCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new vendor.
    """
    db_vendor = Vendor(**vendor.model_dump())
    db.add(db_vendor)
    await db.commit()
    await db.refresh(db_vendor)
    return db_vendor


@app.get(
    "/api/v1/vendors/{vendor_id}",
    response_model=VendorRead,
    tags=["Vendors"],
    summary="Get vendor details"
)
async def get_vendor(
    vendor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get vendor details.
    """
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return vendor


# =============================================================================
# GL Code Endpoints
# =============================================================================
@app.get(
    "/api/v1/gl-codes",
    response_model=GLCodeList,
    tags=["GL Codes"],
    summary="List all GL codes"
)
async def list_gl_codes(
    active_only: bool = Query(True, description="Only show active codes"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all GL codes.
    """
    query = select(GLCode)
    if active_only:
        query = query.where(GLCode.is_active == True)
    if category:
        query = query.where(GLCode.category == category)
    
    query = query.order_by(GLCode.code)
    result = await db.execute(query)
    codes = result.scalars().all()
    
    return GLCodeList(
        items=[GLCodeRead.model_validate(c) for c in codes],
        total=len(codes)
    )


# =============================================================================
# Audit Log Endpoints
# =============================================================================
@app.get(
    "/api/v1/bills/{bill_id}/audit-logs",
    response_model=AuditLogList,
    tags=["Audit"],
    summary="Get bill audit logs"
)
async def get_bill_audit_logs(
    bill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit logs for a bill.
    """
    # Verify bill exists
    bill_result = await db.execute(select(Bill).where(Bill.id == bill_id))
    if not bill_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Get audit logs
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.bill_id == bill_id)
        .order_by(AuditLog.timestamp.desc())
    )
    logs = result.scalars().all()
    
    return AuditLogList(
        items=[AuditLogRead.model_validate(log) for log in logs],
        total=len(logs),
        bill_id=bill_id
    )


# =============================================================================
# Legacy Endpoint (backward compatibility)
# =============================================================================
@app.post("/bills/analyze", tags=["Legacy"], deprecated=True)
async def analyze_bill_legacy(file: UploadFile = File(...)):
    """
    Legacy endpoint - redirects to new upload endpoint.
    """
    # For now, return a message directing to new API
    return {
        "message": "This endpoint is deprecated. Please use POST /api/v1/bills/upload",
        "new_endpoint": "/api/v1/bills/upload"
    }


# =============================================================================
# Main Entry Point
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
