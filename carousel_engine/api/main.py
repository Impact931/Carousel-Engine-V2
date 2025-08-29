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

# Global engine instance
engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global engine
    
    # Startup
    logger.info("Starting Carousel Engine v2", version=config.version)
    
    try:
        # Initialize engine
        engine = CarouselEngine()
        
        # Perform health check
        health_status = await engine.health_check()
        logger.info("Health check completed", status=health_status)
        
        # Check for any unhealthy services
        unhealthy = [k for k, v in health_status["services"].items() if "unhealthy" in str(v)]
        if unhealthy:
            logger.warning("Some services are unhealthy", services=unhealthy)
        
        app.state.engine = engine
        logger.info("Carousel Engine v2 started successfully")
        
    except Exception as e:
        logger.error("Failed to start Carousel Engine", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Carousel Engine v2")


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

# Mount static files
app.mount("/static", StaticFiles(directory="carousel_engine/static"), name="static")

# Include route modules
app.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(carousel.router, prefix="/api", tags=["carousel"])
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