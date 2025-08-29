"""
Health check routes
"""

from fastapi import APIRouter, Request
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/")
async def health_check(request: Request):
    """Basic health check endpoint"""
    try:
        # Get engine from app state
        engine = request.app.state.engine
        
        if not engine:
            return {
                "status": "unhealthy",
                "reason": "Engine not initialized"
            }
        
        # Perform comprehensive health check
        health_status = await engine.health_check()
        
        # Determine overall status
        overall_status = "healthy"
        if "unhealthy" in health_status["engine"] or "degraded" in health_status["engine"]:
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "details": health_status
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "reason": str(e)
        }


@router.get("/services")
async def services_health(request: Request):
    """Detailed service health check"""
    try:
        engine = request.app.state.engine
        
        if not engine:
            return {"error": "Engine not initialized"}
        
        health_status = await engine.health_check()
        return health_status["services"]
        
    except Exception as e:
        logger.error("Services health check failed", error=str(e))
        return {"error": str(e)}


@router.get("/metrics")
async def health_metrics(request: Request):
    """Get processing metrics for monitoring"""
    try:
        engine = request.app.state.engine
        
        if not engine:
            return {"error": "Engine not initialized"}
        
        metrics = engine.get_all_metrics()
        
        # Calculate aggregate metrics
        if metrics:
            total_runs = len(metrics)
            avg_processing_time = sum(m.total_processing_time for m in metrics.values()) / total_runs
            total_image_gen_time = sum(m.image_generation_time for m in metrics.values())
            total_upload_time = sum(m.google_drive_upload_time for m in metrics.values())
            
            return {
                "total_carousel_runs": total_runs,
                "average_processing_time_seconds": round(avg_processing_time, 2),
                "total_image_generation_time_seconds": round(total_image_gen_time, 2),
                "total_upload_time_seconds": round(total_upload_time, 2),
                "recent_runs": list(metrics.keys())[-10:]  # Last 10 runs
            }
        else:
            return {
                "total_carousel_runs": 0,
                "message": "No processing metrics available"
            }
            
    except Exception as e:
        logger.error("Metrics retrieval failed", error=str(e))
        return {"error": str(e)}