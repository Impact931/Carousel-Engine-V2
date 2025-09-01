"""
FastAPI application for Carousel Engine v2
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import structlog

from ..core.config import config
from ..core.engine import CarouselEngine
from ..core.models import CarouselRequest, CarouselResponse, WebhookPayload
from ..core.exceptions import CarouselEngineError
from .routes import webhook, health, carousel, document_upload

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global engine instance (lazy initialization for serverless)
engine = None


def get_or_create_engine():
    """Get or create the engine instance with lazy initialization"""
    global engine
    if engine is None:
        try:
            logger.info("Initializing Carousel Engine v2 (lazy initialization)", version=config.version)
            engine = CarouselEngine()
            logger.info("Carousel Engine v2 initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Carousel Engine", error=str(e))
            # Return None to handle gracefully in endpoints
            return None
    return engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - minimal for serverless compatibility"""
    # Startup
    logger.info("Starting Carousel Engine v2 Application", version=config.version)
    
    # Don't initialize engine here for serverless compatibility
    # Engine will be initialized on first request via get_or_create_engine()
    app.state.get_engine = get_or_create_engine
    logger.info("Carousel Engine v2 application started (engine will initialize on first use)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Carousel Engine v2 application")


# Create FastAPI application
app = FastAPI(
    title="Carousel Engine v2",
    description="Automated Facebook carousel content generation",
    version=config.version,
    docs_url="/docs" if config.is_development else None,
    redoc_url="/redoc" if config.is_development else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"] if config.is_development else [],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Mount static files (conditional for serverless environments)
try:
    import os
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"Static files mounted from: {static_dir}")
    else:
        logger.warning(f"Static directory not found: {static_dir}")
except Exception as e:
    logger.warning(f"Failed to mount static files: {e}")

# Include route modules
app.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(carousel.router, prefix="/api/carousel", tags=["carousel"])
app.include_router(document_upload.router, prefix="/api", tags=["document-upload"])


@app.exception_handler(CarouselEngineError)
async def carousel_engine_exception_handler(request: Request, exc: CarouselEngineError):
    """Handle Carousel Engine specific exceptions"""
    logger.error(
        "Carousel engine error",
        error_code=exc.error_code,
        message=exc.message,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=400,
        content={
            "error": True,
            "error_code": exc.error_code,
            "message": exc.message,
            "timestamp": time.time()
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.error(
        "HTTP error",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(
        "Unexpected error",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "timestamp": time.time()
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Carousel Engine v2",
        "version": config.version,
        "status": "running",
        "docs_url": "/docs" if config.is_development else None
    }


@app.get("/version")
async def version():
    """Get application version"""
    return {
        "version": config.version,
        "environment": config.environment
    }