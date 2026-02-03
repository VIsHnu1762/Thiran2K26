"""
BillAgent Pro - Async Bill Processing Task
===========================================
Celery task for asynchronous bill processing.

This task:
1. Receives image bytes and metadata
2. Runs the full processing pipeline via BillProcessingService
3. Updates progress in Redis at each stage
4. Returns bill_id on completion

Usage:
    from tasks.process_bill import process_bill_task
    
    # Trigger async processing
    result = process_bill_task.delay(
        image_bytes_b64="...",  # Base64 encoded
        image_url="/path/to/image.jpg",
        user_id="user-123",
    )
    
    # Get task ID
    task_id = result.id
    
    # Check status later
    status = result.status  # PENDING, STARTED, SUCCESS, FAILURE
    result = result.get()   # Block until complete (not recommended)
"""

import asyncio
import base64
import logging
import sys
import os
from typing import Any, Dict, Optional

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery import current_task
from celery.exceptions import SoftTimeLimitExceeded

from celery_app import celery_app, TaskProgress

logger = logging.getLogger(__name__)


# =============================================================================
# Progress Stage Definitions
# =============================================================================
PROGRESS_STAGES = {
    "queued": {"percent": 0, "message": "Task queued for processing"},
    "started": {"percent": 5, "message": "Processing started"},
    "digitization": {"percent": 25, "message": "Running OCR extraction..."},
    "digitization_complete": {"percent": 40, "message": "OCR extraction complete"},
    "validation": {"percent": 50, "message": "Validating bill data..."},
    "validation_complete": {"percent": 65, "message": "Validation complete"},
    "duplicate_check": {"percent": 70, "message": "Checking for duplicates..."},
    "duplicate_complete": {"percent": 80, "message": "Duplicate check complete"},
    "gl_assignment": {"percent": 85, "message": "Assigning GL codes..."},
    "gl_complete": {"percent": 95, "message": "GL codes assigned"},
    "completed": {"percent": 100, "message": "Processing complete"},
}


def update_progress(task_id: str, stage: str, extra_data: dict = None):
    """Update task progress in Redis."""
    stage_info = PROGRESS_STAGES.get(stage, {"percent": 0, "message": stage})
    progress = TaskProgress(task_id)
    progress.update(
        stage=stage,
        percent=stage_info["percent"],
        message=stage_info["message"],
        data=extra_data,
    )


async def run_bill_processing(
    image_bytes: bytes,
    image_url: str,
    task_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the async bill processing pipeline.
    
    This is the core processing function that runs in an async context.
    """
    from app.config import get_settings
    from app.database import AsyncSessionLocal
    from app.services.bill_service import BillProcessingService
    
    settings = get_settings()
    progress = TaskProgress(task_id)
    
    # Create database session
    async with AsyncSessionLocal() as db:
        try:
            # Initialize service
            service = BillProcessingService()
            
            # Update progress: Digitization starting
            update_progress(task_id, "digitization")
            
            # Process bill with task_id tracking
            result = await service.process_bill(
                image_bytes=image_bytes,
                image_url=image_url,
                db=db,
                user_id=user_id,
                task_id=task_id,
            )
            
            # Commit the transaction
            await db.commit()
            
            # Convert result to dict
            result_dict = result.to_dict()
            
            # Mark as complete
            if result.status == "FAILED":
                progress.fail(
                    error=result.errors[0].get("message", "Processing failed") if result.errors else "Unknown error",
                    stage="processing",
                    data=result_dict,
                )
            else:
                progress.complete(
                    bill_id=str(result.bill_id) if result.bill_id else None,
                    result_data=result_dict,
                )
            
            return result_dict
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Bill processing failed: {e}", exc_info=True)
            progress.fail(
                error=str(e),
                stage="processing",
            )
            raise


@celery_app.task(
    name="tasks.process_bill.process_bill_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    track_started=True,
    acks_late=True,
)
def process_bill_task(
    self,
    image_bytes_b64: str,
    image_url: str,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Celery task for processing a bill asynchronously.
    
    Args:
        image_bytes_b64: Base64 encoded image bytes
        image_url: Path/URL where image is stored
        user_id: User who uploaded the bill
        metadata: Additional metadata (filename, content_type, etc.)
    
    Returns:
        Dict with bill_id, status, and processing details
    """
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Starting bill processing for {image_url}")
    
    progress = TaskProgress(task_id)
    
    try:
        # Update progress: Started
        update_progress(task_id, "started", extra_data={"image_url": image_url})
        
        # Decode image bytes
        try:
            image_bytes = base64.b64decode(image_bytes_b64)
        except Exception as e:
            logger.error(f"[Task {task_id}] Failed to decode image: {e}")
            progress.fail(
                error=f"Invalid image data: {str(e)}",
                stage="started",
            )
            raise ValueError(f"Invalid base64 image data: {e}")
        
        # Run async processing
        # Create new event loop for Celery worker
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                run_bill_processing(
                    image_bytes=image_bytes,
                    image_url=image_url,
                    task_id=task_id,
                    user_id=user_id,
                )
            )
        finally:
            loop.close()
        
        logger.info(
            f"[Task {task_id}] Bill processing complete: "
            f"bill_id={result.get('bill_id')}, status={result.get('status')}"
        )
        
        return result
        
    except SoftTimeLimitExceeded:
        logger.error(f"[Task {task_id}] Task timed out")
        progress.fail(
            error="Processing timed out. The bill may be too complex or the service is overloaded.",
            stage="timeout",
        )
        raise
        
    except Exception as e:
        logger.error(f"[Task {task_id}] Task failed: {e}", exc_info=True)
        
        # Check if we should retry
        if self.request.retries < self.max_retries:
            logger.info(f"[Task {task_id}] Scheduling retry {self.request.retries + 1}/{self.max_retries}")
            progress.update(
                stage="retrying",
                percent=0,
                message=f"Retrying... (attempt {self.request.retries + 1}/{self.max_retries})",
            )
            raise self.retry(exc=e)
        
        # No more retries
        progress.fail(error=str(e), stage="failed")
        raise


@celery_app.task(
    name="tasks.process_bill.process_bill_batch",
    bind=True,
    max_retries=1,
)
def process_bill_batch(
    self,
    bills: list,
) -> Dict[str, Any]:
    """
    Process multiple bills in batch.
    
    Args:
        bills: List of dicts with image_bytes_b64, image_url, user_id
    
    Returns:
        Dict with task_ids for each bill
    """
    task_id = self.request.id
    logger.info(f"[Batch {task_id}] Processing {len(bills)} bills")
    
    results = []
    for idx, bill_data in enumerate(bills):
        # Trigger individual tasks
        result = process_bill_task.delay(
            image_bytes_b64=bill_data["image_bytes_b64"],
            image_url=bill_data.get("image_url", f"batch_{task_id}_{idx}"),
            user_id=bill_data.get("user_id"),
            metadata=bill_data.get("metadata"),
        )
        results.append({
            "index": idx,
            "task_id": result.id,
            "image_url": bill_data.get("image_url"),
        })
    
    return {
        "batch_id": task_id,
        "total": len(bills),
        "tasks": results,
    }


# =============================================================================
# Task Status Helpers
# =============================================================================
def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the current status of a bill processing task.
    
    Returns combined info from Celery and Redis progress tracking.
    """
    from celery.result import AsyncResult
    
    # Get Celery task state
    result = AsyncResult(task_id, app=celery_app)
    
    # Get progress from Redis
    progress = TaskProgress.get_progress(task_id)
    bill_id = TaskProgress.get_bill_id(task_id)
    
    status = {
        "task_id": task_id,
        "celery_status": result.status,
        "bill_id": bill_id,
    }
    
    if progress:
        status.update({
            "stage": progress.get("stage"),
            "percent": progress.get("percent", 0),
            "message": progress.get("message"),
            "status": progress.get("status"),
            "error": progress.get("error"),
            "updated_at": progress.get("updated_at"),
            "data": progress.get("data"),
        })
    else:
        # Fallback to Celery status only
        status.update({
            "stage": "unknown",
            "percent": 0 if result.status == "PENDING" else 100 if result.status == "SUCCESS" else 0,
            "message": f"Task {result.status.lower()}",
            "status": result.status.lower(),
        })
    
    # Add result if task completed
    if result.status == "SUCCESS" and result.result:
        status["result"] = result.result
    elif result.status == "FAILURE":
        status["error"] = str(result.result) if result.result else "Unknown error"
        status["status"] = "failed"
    
    return status


def cancel_task(task_id: str) -> bool:
    """
    Cancel a pending or running task.
    
    Returns True if task was successfully cancelled.
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    # Revoke the task
    celery_app.control.revoke(task_id, terminate=True)
    
    # Update progress
    progress = TaskProgress(task_id)
    progress.fail(error="Task cancelled by user", stage="cancelled")
    
    return True


__all__ = [
    "process_bill_task",
    "process_bill_batch",
    "get_task_status",
    "cancel_task",
    "update_progress",
]
