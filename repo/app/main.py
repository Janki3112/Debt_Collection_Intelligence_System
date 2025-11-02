"""
Debt Collection Intelligence System - Main Application
Production-ready FastAPI application with comprehensive error handling,
logging, metrics, and security features.
"""
import sys
import io

# Force UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
import os

from app.api import ingest, extract, ask, audit, admin, webhooks
from app.db.session import init_db, close_db
from app.logger import logger
from app.metrics import MetricsMiddleware, metrics_registry


# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting Debt Collection Intelligence System...")
    logger.info(f"GROQ Model: {os.getenv('GROQ_MODEL', 'Not configured')}")
    
    # Verify critical environment variables
    if not os.getenv('GROQ_API_KEY'):
        logger.error("GROQ_API_KEY not found in environment!")
    if not os.getenv('DB_URL'):
        logger.error("DB_URL not found in environment!")
    
    await init_db()
    logger.info("Database initialized")
    
    # Ensure directories exist
    os.makedirs(os.getenv("STORAGE_PATH", "./storage"), exist_ok=True)
    os.makedirs("./data", exist_ok=True)
    os.makedirs("./logs", exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Debt Collection Intelligence System...")
    await close_db()
    logger.info("Database connections closed")

# Create FastAPI app
app = FastAPI(
    title="Debt Collection Intelligence System",
    description="Production-ready API for contract analysis, extraction, and Q&A",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error occurred"}
    )

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"status={response.status_code} duration={duration:.3f}s"
    )
    
    # Add timing header
    response.headers["X-Process-Time"] = str(duration)
    
    return response

# Include routers
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(extract.router, prefix="/extract", tags=["Extract"])
app.include_router(ask.router, prefix="/ask", tags=["Ask/Q&A"])
app.include_router(audit.router, prefix="/audit", tags=["Audit"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(admin.router, prefix="", tags=["Admin"])

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Debt Collection Intelligence System",
        "version": "1.0.0",
        "status": "operational",
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "groq_model": os.getenv("GROQ_MODEL", "not-configured"),
        "endpoints": {
            "docs": "/docs",
            "health": "/healthz",
            "metrics": "/metrics"
        }
    }