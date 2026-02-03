"""
BillAgent Pro - Health & Monitoring Endpoints
==============================================
Comprehensive health checks and monitoring endpoints for production.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import time
import os
import psutil
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from pydantic import BaseModel
import redis

from app.database import get_db
from app.config import settings

# Try to import Celery
try:
    from celery_app import celery_app, REDIS_URL
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    celery_app = None
    REDIS_URL = settings.redis_url


router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


# =============================================================================
# Response Models
# =============================================================================
class HealthStatus(BaseModel):
    """Basic health status."""
    status: str
    version: str
    environment: str
    timestamp: datetime


class DetailedHealthStatus(BaseModel):
    """Detailed health status with component checks."""
    status: str
    version: str
    environment: str
    uptime_seconds: float
    checks: Dict[str, Dict[str, Any]]
    timestamp: datetime


class ReadinessStatus(BaseModel):
    """Kubernetes readiness probe status."""
    ready: bool
    checks: Dict[str, bool]
    timestamp: datetime


class LivenessStatus(BaseModel):
    """Kubernetes liveness probe status."""
    alive: bool
    timestamp: datetime


class MetricsResponse(BaseModel):
    """System metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_percent: float
    open_files: int
    active_connections: int
    timestamp: datetime


# Track application start time
_app_start_time = datetime.utcnow()


# =============================================================================
# Helper Functions
# =============================================================================
async def check_database(db: AsyncSession) -> Dict[str, Any]:
    """Check database connectivity and basic metrics."""
    start = time.time()
    try:
        # Test connection
        result = await db.execute(select(func.now()))
        db_time = result.scalar()
        
        # Get connection pool stats (if available)
        latency = (time.time() - start) * 1000
        
        return {
            "status": "healthy",
            "latency_ms": round(latency, 2),
            "server_time": db_time.isoformat() if db_time else None,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.time() - start) * 1000, 2),
        }


def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    start = time.time()
    try:
        r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        if r.ping():
            info = r.info("server")
            latency = (time.time() - start) * 1000
            r.close()
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }
        r.close()
        return {"status": "unhealthy", "error": "Ping failed"}
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.time() - start) * 1000, 2),
        }


def check_celery() -> Dict[str, Any]:
    """Check Celery worker availability."""
    if not CELERY_AVAILABLE or not celery_app:
        return {"status": "not_configured"}
    
    start = time.time()
    try:
        inspect = celery_app.control.inspect(timeout=2)
        ping_response = inspect.ping()
        
        if ping_response:
            worker_count = len(ping_response)
            active_tasks = inspect.active() or {}
            total_active = sum(len(tasks) for tasks in active_tasks.values())
            
            return {
                "status": "healthy",
                "latency_ms": round((time.time() - start) * 1000, 2),
                "workers": worker_count,
                "active_tasks": total_active,
            }
        return {
            "status": "unhealthy",
            "error": "No workers available",
            "latency_ms": round((time.time() - start) * 1000, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.time() - start) * 1000, 2),
        }


def get_system_metrics() -> Dict[str, Any]:
    """Get system resource metrics."""
    try:
        process = psutil.Process()
        
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": process.memory_info().rss / 1024 / 1024,
            "disk_percent": psutil.disk_usage("/").percent,
            "open_files": len(process.open_files()),
            "threads": process.num_threads(),
            "process_cpu_percent": process.cpu_percent(interval=0.1),
        }
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Endpoints
# =============================================================================
@router.get("/health", response_model=HealthStatus)
async def basic_health():
    """
    Basic health check endpoint.
    Returns 200 if the API is running.
    """
    return HealthStatus(
        status="healthy",
        version=getattr(settings, 'api_version', '1.0.0'),
        environment=settings.environment,
        timestamp=datetime.utcnow(),
    )


@router.get("/health/detailed", response_model=DetailedHealthStatus)
async def detailed_health(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check with all component statuses.
    """
    # Run all checks
    db_status = await check_database(db)
    redis_status = check_redis()
    celery_status = check_celery()
    system_metrics = get_system_metrics()
    
    # Determine overall status
    checks = {
        "database": db_status,
        "redis": redis_status,
        "celery": celery_status,
        "system": system_metrics,
    }
    
    # Overall status is healthy if critical services are healthy
    critical_healthy = (
        db_status.get("status") == "healthy" and
        redis_status.get("status") in ["healthy", "not_configured"]
    )
    
    overall_status = "healthy" if critical_healthy else "degraded"
    
    # Calculate uptime
    uptime = (datetime.utcnow() - _app_start_time).total_seconds()
    
    return DetailedHealthStatus(
        status=overall_status,
        version=getattr(settings, 'api_version', '1.0.0'),
        environment=settings.environment,
        uptime_seconds=uptime,
        checks=checks,
        timestamp=datetime.utcnow(),
    )


@router.get("/ready", response_model=ReadinessStatus)
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """
    Kubernetes readiness probe.
    Returns 200 if the service is ready to accept traffic.
    """
    db_status = await check_database(db)
    redis_status = check_redis()
    
    checks = {
        "database": db_status.get("status") == "healthy",
        "redis": redis_status.get("status") in ["healthy", "not_configured"],
    }
    
    is_ready = all(checks.values())
    
    response = ReadinessStatus(
        ready=is_ready,
        checks=checks,
        timestamp=datetime.utcnow(),
    )
    
    if not is_ready:
        return JSONResponse(
            status_code=503,
            content=response.model_dump(mode="json"),
        )
    
    return response


@router.get("/live", response_model=LivenessStatus)
async def liveness_probe():
    """
    Kubernetes liveness probe.
    Returns 200 if the service is alive (not deadlocked).
    """
    # Simple check - if we can respond, we're alive
    return LivenessStatus(
        alive=True,
        timestamp=datetime.utcnow(),
    )


@router.get("/metrics", response_model=MetricsResponse)
async def system_metrics():
    """
    System resource metrics.
    """
    metrics = get_system_metrics()
    
    if "error" in metrics:
        raise HTTPException(status_code=500, detail=metrics["error"])
    
    return MetricsResponse(
        cpu_percent=metrics["cpu_percent"],
        memory_percent=metrics["memory_percent"],
        memory_used_mb=metrics["memory_used_mb"],
        disk_percent=metrics["disk_percent"],
        open_files=metrics["open_files"],
        active_connections=metrics.get("threads", 0),
        timestamp=datetime.utcnow(),
    )


@router.get("/prometheus")
async def prometheus_metrics(db: AsyncSession = Depends(get_db)):
    """
    Prometheus-compatible metrics endpoint.
    Returns metrics in Prometheus text format.
    """
    # Get all metrics
    db_status = await check_database(db)
    redis_status = check_redis()
    celery_status = check_celery()
    system = get_system_metrics()
    uptime = (datetime.utcnow() - _app_start_time).total_seconds()
    
    # Format as Prometheus metrics
    lines = [
        "# HELP billagent_up Whether the service is up",
        "# TYPE billagent_up gauge",
        f'billagent_up{{environment="{settings.environment}"}} 1',
        "",
        "# HELP billagent_uptime_seconds Service uptime in seconds",
        "# TYPE billagent_uptime_seconds counter",
        f"billagent_uptime_seconds {uptime}",
        "",
        "# HELP billagent_database_up Database connection status",
        "# TYPE billagent_database_up gauge",
        f'billagent_database_up {1 if db_status.get("status") == "healthy" else 0}',
        "",
        "# HELP billagent_database_latency_ms Database query latency",
        "# TYPE billagent_database_latency_ms gauge",
        f'billagent_database_latency_ms {db_status.get("latency_ms", 0)}',
        "",
        "# HELP billagent_redis_up Redis connection status",
        "# TYPE billagent_redis_up gauge",
        f'billagent_redis_up {1 if redis_status.get("status") == "healthy" else 0}',
        "",
        "# HELP billagent_celery_workers Number of Celery workers",
        "# TYPE billagent_celery_workers gauge",
        f'billagent_celery_workers {celery_status.get("workers", 0)}',
        "",
        "# HELP billagent_cpu_percent CPU usage percentage",
        "# TYPE billagent_cpu_percent gauge",
        f'billagent_cpu_percent {system.get("cpu_percent", 0)}',
        "",
        "# HELP billagent_memory_percent Memory usage percentage",
        "# TYPE billagent_memory_percent gauge",
        f'billagent_memory_percent {system.get("memory_percent", 0)}',
        "",
        "# HELP billagent_memory_used_bytes Memory used in bytes",
        "# TYPE billagent_memory_used_bytes gauge",
        f'billagent_memory_used_bytes {system.get("memory_used_mb", 0) * 1024 * 1024}',
        "",
        "# HELP billagent_disk_percent Disk usage percentage",
        "# TYPE billagent_disk_percent gauge",
        f'billagent_disk_percent {system.get("disk_percent", 0)}',
        "",
    ]
    
    return JSONResponse(
        content="\n".join(lines),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/info")
async def app_info():
    """
    Application information endpoint.
    """
    return {
        "app": "BillAgent Pro",
        "version": getattr(settings, 'api_version', '1.0.0'),
        "environment": settings.environment,
        "debug": settings.debug,
        "python_version": os.sys.version,
        "started_at": _app_start_time.isoformat(),
        "uptime_seconds": (datetime.utcnow() - _app_start_time).total_seconds(),
        "features": {
            "ocr_engine": settings.ocr_primary_engine,
            "celery_available": CELERY_AVAILABLE,
            "sentry_enabled": bool(settings.sentry_dsn),
        },
    }
