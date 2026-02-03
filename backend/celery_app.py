"""
BillAgent Pro - Celery Application Configuration
=================================================
Configures Celery with Redis broker for async bill processing.

Usage:
    # Start worker
    celery -A celery_app worker --loglevel=info
    
    # Start worker with concurrency
    celery -A celery_app worker --loglevel=info --concurrency=4
    
    # Start Flower monitoring (optional)
    celery -A celery_app flower --port=5555
"""

import os
from celery import Celery
from kombu import Queue

# Redis configuration from environment or defaults
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Build Redis URL
if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# Backend URL for result storage (use database 1 for results)
if REDIS_PASSWORD:
    RESULT_BACKEND_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1"
else:
    RESULT_BACKEND_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"


def create_celery_app() -> Celery:
    """
    Create and configure the Celery application.
    
    Returns:
        Configured Celery app instance
    """
    app = Celery(
        "billagent",
        broker=REDIS_URL,
        backend=RESULT_BACKEND_URL,
        include=[
            "tasks.process_bill",
        ],
    )
    
    # ===========================================================================
    # Celery Configuration
    # ===========================================================================
    app.conf.update(
        # Task Settings
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        
        # Result Settings
        result_expires=86400,  # Results expire after 24 hours
        result_extended=True,  # Include task_id, status, etc. in result
        
        # Task Execution Settings
        task_acks_late=True,  # Acknowledge after completion
        task_reject_on_worker_lost=True,  # Requeue if worker dies
        task_time_limit=300,  # Hard limit: 5 minutes per task
        task_soft_time_limit=240,  # Soft limit: 4 minutes (raises exception)
        
        # Worker Settings
        worker_prefetch_multiplier=1,  # Process one task at a time
        worker_concurrency=4,  # Default workers per process
        worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (memory cleanup)
        
        # Retry Settings
        task_default_retry_delay=30,  # Wait 30 seconds between retries
        task_max_retries=3,  # Maximum retry attempts
        
        # Queue Settings
        task_queues=(
            Queue("default", routing_key="default"),
            Queue("bills", routing_key="bills.#"),
            Queue("ocr", routing_key="ocr.#"),
        ),
        task_default_queue="default",
        task_default_exchange="billagent",
        task_default_routing_key="default",
        
        # Route bill tasks to dedicated queue
        task_routes={
            "tasks.process_bill.*": {"queue": "bills", "routing_key": "bills.process"},
            "tasks.process_bill.process_bill_task": {"queue": "bills"},
        },
        
        # Beat Schedule (for periodic tasks if needed)
        beat_schedule={
            # Example: cleanup old tasks every hour
            # "cleanup-old-tasks": {
            #     "task": "tasks.cleanup.cleanup_old_tasks",
            #     "schedule": 3600.0,
            # },
        },
    )
    
    return app


# Create the Celery app instance
celery_app = create_celery_app()


# ===========================================================================
# Task Progress Tracking
# ===========================================================================
class TaskProgress:
    """
    Helper class to track and update task progress in Redis.
    
    Usage:
        progress = TaskProgress(task_id)
        progress.update(stage="digitization", percent=25, message="Running OCR...")
        progress.complete(bill_id=uuid)
        progress.fail(error="OCR failed")
    """
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self._redis = None
    
    @property
    def redis(self):
        """Lazy Redis connection."""
        if self._redis is None:
            import redis
            self._redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        return self._redis
    
    @property
    def key(self) -> str:
        """Redis key for this task's progress."""
        return f"task_progress:{self.task_id}"
    
    def update(
        self,
        stage: str,
        percent: int,
        message: str = "",
        data: dict = None,
    ) -> None:
        """
        Update task progress.
        
        Args:
            stage: Current processing stage
            percent: Completion percentage (0-100)
            message: Human-readable status message
            data: Additional data to store
        """
        import json
        from datetime import datetime
        
        progress_data = {
            "task_id": self.task_id,
            "stage": stage,
            "percent": min(100, max(0, percent)),
            "message": message,
            "status": "processing",
            "updated_at": datetime.utcnow().isoformat(),
            "data": data or {},
        }
        
        # Store with 24-hour expiry
        self.redis.setex(
            self.key,
            86400,
            json.dumps(progress_data),
        )
    
    def complete(self, bill_id: str, result_data: dict = None) -> None:
        """Mark task as completed."""
        import json
        from datetime import datetime
        
        progress_data = {
            "task_id": self.task_id,
            "stage": "completed",
            "percent": 100,
            "message": "Bill processed successfully",
            "status": "completed",
            "bill_id": bill_id,
            "updated_at": datetime.utcnow().isoformat(),
            "data": result_data or {},
        }
        
        self.redis.setex(
            self.key,
            86400,
            json.dumps(progress_data),
        )
        
        # Also store task_id → bill_id mapping
        self.redis.setex(
            f"task_bill_mapping:{self.task_id}",
            86400,
            bill_id,
        )
    
    def fail(self, error: str, stage: str = "unknown", data: dict = None) -> None:
        """Mark task as failed."""
        import json
        from datetime import datetime
        
        progress_data = {
            "task_id": self.task_id,
            "stage": stage,
            "percent": 0,
            "message": error,
            "status": "failed",
            "error": error,
            "updated_at": datetime.utcnow().isoformat(),
            "data": data or {},
        }
        
        self.redis.setex(
            self.key,
            86400,
            json.dumps(progress_data),
        )
    
    @classmethod
    def get_progress(cls, task_id: str) -> dict:
        """Get progress for a task."""
        import json
        import redis as redis_lib
        
        r = redis_lib.Redis.from_url(REDIS_URL, decode_responses=True)
        key = f"task_progress:{task_id}"
        data = r.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    @classmethod
    def get_bill_id(cls, task_id: str) -> str:
        """Get bill_id for a completed task."""
        import redis as redis_lib
        
        r = redis_lib.Redis.from_url(REDIS_URL, decode_responses=True)
        return r.get(f"task_bill_mapping:{task_id}")


# Export for easy import
__all__ = ["celery_app", "TaskProgress", "REDIS_URL"]
