"""
Carousel generation API routes
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from typing import Dict, Any
import structlog

from ...core.models import CarouselRequest, CarouselResponse

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/generate", response_model=CarouselResponse)
async def generate_carousel(
    request: CarouselRequest,
    req: Request
) -> CarouselResponse:
    """Generate carousel from Notion page (synchronous)
    
    This endpoint generates a carousel synchronously and returns the result.
    Use this for manual testing or when you need immediate results.
    """
    try:
        logger.info("Manual carousel generation requested", page_id=request.notion_page_id)
        
        # Get engine from app state
        engine = req.app.state.engine
        
        if not engine:
            raise HTTPException(status_code=500, detail="Engine not initialized")
        
        # Generate carousel
        result = await engine.generate_carousel(
            request.notion_page_id,
            request.force_regenerate
        )
        
        logger.info(
            "Manual carousel generation completed",
            page_id=request.notion_page_id,
            success=result.success,
            slides=result.slides_generated
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Manual carousel generation failed",
            page_id=request.notion_page_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-async")
async def generate_carousel_async(
    request: CarouselRequest,
    background_tasks: BackgroundTasks,
    req: Request
) -> Dict[str, Any]:
    """Generate carousel from Notion page (asynchronous)
    
    This endpoint queues a carousel generation job and returns immediately.
    Use this for webhook-style processing where you don't need immediate results.
    """
    try:
        logger.info("Async carousel generation requested", page_id=request.notion_page_id)
        
        # Get engine from app state
        engine = req.app.state.engine
        
        if not engine:
            raise HTTPException(status_code=500, detail="Engine not initialized")
        
        # Queue generation in background
        background_tasks.add_task(
            _background_generate_carousel,
            engine,
            request.notion_page_id,
            request.force_regenerate
        )
        
        return {
            "status": "queued",
            "notion_page_id": request.notion_page_id,
            "message": "Carousel generation queued for background processing"
        }
        
    except Exception as e:
        logger.error(
            "Async carousel generation queueing failed",
            page_id=request.notion_page_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{page_id}")
async def get_carousel_status(page_id: str, req: Request) -> Dict[str, Any]:
    """Get carousel generation status for a Notion page"""
    try:
        logger.info("Carousel status requested", page_id=page_id)
        
        # Get engine from app state
        engine = req.app.state.engine
        
        if not engine:
            raise HTTPException(status_code=500, detail="Engine not initialized")
        
        # Get page status from Notion
        page = await engine.notion.get_page(page_id)
        
        # Get processing metrics if available
        metrics = engine.get_processing_metrics(page_id)
        
        response = {
            "notion_page_id": page_id,
            "title": page.title,
            "status": page.status.value,
            "format": page.format.value,
            "google_folder_url": page.google_folder_url,
            "last_edited_time": page.last_edited_time.isoformat(),
            "has_content": bool(page.content and page.content.strip())
        }
        
        if metrics:
            response["processing_metrics"] = {
                "total_processing_time": metrics.total_processing_time,
                "image_generation_time": metrics.image_generation_time,
                "google_drive_upload_time": metrics.google_drive_upload_time,
                "processed_at": metrics.timestamp.isoformat()
            }
        
        return response
        
    except Exception as e:
        logger.error("Status retrieval failed", page_id=page_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_recent_carousels(req: Request, limit: int = 10) -> Dict[str, Any]:
    """List recent carousel processing metrics"""
    try:
        # Get engine from app state
        engine = req.app.state.engine
        
        if not engine:
            raise HTTPException(status_code=500, detail="Engine not initialized")
        
        all_metrics = engine.get_all_metrics()
        
        # Sort by timestamp, most recent first
        sorted_metrics = sorted(
            all_metrics.values(),
            key=lambda m: m.timestamp,
            reverse=True
        )
        
        # Limit results
        recent_metrics = sorted_metrics[:limit]
        
        # Format response
        carousel_list = []
        for metric in recent_metrics:
            carousel_list.append({
                "notion_page_id": metric.notion_page_id,
                "processing_time": metric.total_processing_time,
                "image_generation_time": metric.image_generation_time,
                "processed_at": metric.timestamp.isoformat()
            })
        
        return {
            "total_processed": len(all_metrics),
            "showing": len(carousel_list),
            "carousels": carousel_list
        }
        
    except Exception as e:
        logger.error("Carousel list retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def _background_generate_carousel(
    engine,
    page_id: str,
    force_regenerate: bool = False
) -> None:
    """Background task for carousel generation"""
    try:
        logger.info("Starting background carousel generation", page_id=page_id)
        
        result = await engine.generate_carousel(page_id, force_regenerate)
        
        if result.success:
            logger.info(
                "Background carousel generation completed successfully",
                page_id=page_id,
                slides_generated=result.slides_generated,
                processing_time=result.processing_time_seconds
            )
        else:
            logger.error(
                "Background carousel generation failed",
                page_id=page_id,
                error=result.error_message
            )
            
    except Exception as e:
        logger.error(
            "Background carousel generation task failed",
            page_id=page_id,
            error=str(e)
        )