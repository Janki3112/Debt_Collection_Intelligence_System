"""
Admin and monitoring endpoints
"""
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any
import os
import psutil
from datetime import datetime

from app.metrics import get_metrics_text, metrics_registry
from app.logger import logger

router = APIRouter()

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str
    environment: str

class MetricsResponse(BaseModel):
    """Metrics summary response"""
    ingest_count: int
    ask_count: int
    extract_count: int
    audit_count: int
    active_requests: int
    uptime_seconds: float

class SystemInfo(BaseModel):
    """System information"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    python_version: str

# Track startup time
startup_time = datetime.utcnow()

@router.get("/healthz", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns 200 if service is healthy
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "development")
    )

@router.get("/readyz")
async def readiness_check():
    """
    Readiness check for Kubernetes/container orchestration
    Returns 200 when service is ready to accept traffic
    """
    # Could add database connectivity check here
    try:
        # Check if FAISS index is loaded
        from app.core.embeddings import _index
        
        return {
            "status": "ready",
            "checks": {
                "index_loaded": _index is not None
            }
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return Response(
            content={"status": "not ready", "error": str(e)},
            status_code=503
        )

@router.get("/metrics")
async def metrics_endpoint():
    """
    Metrics endpoint - returns JSON format
    For Prometheus text format, use /metrics/prometheus
    """
    try:
        from app.db.crud import get_db_stats
        from app.metrics import (
            INGEST_COUNT, INGEST_PAGES, ASK_COUNT, EXTRACT_COUNT, 
            AUDIT_COUNT, ACTIVE_REQUESTS, CHUNK_COUNT
        )
        
        # Get database stats
        try:
            stats = await get_db_stats()
        except Exception as e:
            logger.warning(f"Could not get DB stats: {e}")
            stats = {"documents": 0, "chunks": 0, "pages": 0}
        
        uptime = (datetime.utcnow() - startup_time).total_seconds()
        
        return {
            "documents": stats.get("documents", 0),
            "chunks": stats.get("chunks", 0),
            "pages": stats.get("pages", 0),
            "uptime_seconds": uptime,
            "ingest_count": INGEST_COUNT._value.get(),
            "ingest_pages": INGEST_PAGES._value.get(),
            "ask_count": ASK_COUNT._value.get(),
            "extract_count": EXTRACT_COUNT._value.get(),
            "audit_count": AUDIT_COUNT._value.get(),
            "chunk_count": CHUNK_COUNT._value.get(),
            "active_requests": ACTIVE_REQUESTS._value.get(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Metrics endpoint error: {str(e)}", exc_info=True)
        # Return basic metrics even if DB is down
        return {
            "documents": 0,
            "chunks": 0,
            "pages": 0,
            "error": str(e)
        }

@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def prometheus_metrics():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus exposition format
    """
    return get_metrics_text()

@router.get("/metrics/summary", response_model=Dict[str, Any])
async def metrics_summary():
    """
    Human-readable metrics summary
    """
    from app.metrics import (
        INGEST_COUNT, ASK_COUNT, EXTRACT_COUNT, 
        AUDIT_COUNT, ACTIVE_REQUESTS
    )
    
    uptime = (datetime.utcnow() - startup_time).total_seconds()
    
    return {
        "uptime_seconds": uptime,
        "ingest_documents": INGEST_COUNT._value.get(),
        "ask_questions": ASK_COUNT._value.get(),
        "extract_requests": EXTRACT_COUNT._value.get(),
        "audit_requests": AUDIT_COUNT._value.get(),
        "active_requests": ACTIVE_REQUESTS._value.get(),
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/system", response_model=SystemInfo)
async def system_info():
    """
    System resource information
    Useful for monitoring and debugging
    """
    import sys
    
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return SystemInfo(
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_percent=memory.percent,
        disk_usage_percent=disk.percent,
        python_version=sys.version
    )

@router.post("/reload-index")
async def reload_index():
    """
    Reload FAISS index from disk
    Useful after manual index updates
    """
    try:
        from app.core.embeddings import _ensure_index
        
        # Force reload
        import app.core.embeddings as emb
        emb._index = None
        emb._meta = None
        
        _ensure_index()
        
        logger.info("Index reloaded successfully")
        return {"status": "success", "message": "Index reloaded"}
        
    except Exception as e:
        logger.error(f"Index reload failed: {str(e)}")
        return Response(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@router.get("/config")
async def get_config():
    """
    Get current configuration (non-sensitive values only)
    """
    return {
        "embedding_model": os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        "storage_path": os.getenv("STORAGE_PATH", "./storage"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "rate_limit_enabled": os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true",
        "max_file_size_mb": int(os.getenv("MAX_FILE_SIZE_MB", "50")),
        "log_level": os.getenv("LOG_LEVEL", "INFO")
    }