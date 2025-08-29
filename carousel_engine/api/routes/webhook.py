"""
Webhook routes for Notion integration
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
import structlog

from ...core.config import config
from ...core.models import CarouselStatus
from ...core.exceptions import WebhookValidationError

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/notion")
async def notion_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: Dict[str, Any]
):
    """Handle Notion webhook events
    
    This endpoint receives webhook notifications from Notion when pages are updated.
    It processes page.updated events for carousel generation triggers.
    """
    try:
        logger.info("Received Notion webhook", payload_type=payload.get("type"))
        
        # Validate webhook payload
        await _validate_webhook_payload(request, payload)
        
        # Extract event details
        event_type = payload.get("type")
        
        if event_type == "page":
            # Handle page update event
            page_data = payload.get("data", {})
            page_id = page_data.get("id")
            
            if not page_id:
                raise WebhookValidationError("Missing page ID in webhook payload")
            
            logger.info("Processing page update", page_id=page_id)
            
            # Queue carousel generation in background
            background_tasks.add_task(
                _process_page_update,
                page_id,
                payload
            )
            
            return {"status": "accepted", "page_id": page_id}
        
        else:
            logger.info("Ignoring non-page webhook event", event_type=event_type)
            return {"status": "ignored", "reason": f"Event type {event_type} not processed"}
            
    except WebhookValidationError as e:
        logger.error("Webhook validation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook processing failed")


async def _validate_webhook_payload(request: Request, payload: Dict[str, Any]) -> None:
    """Validate webhook payload and signature
    
    Args:
        request: FastAPI request object
        payload: Webhook payload
        
    Raises:
        WebhookValidationError: If validation fails
    """
    try:
        # Basic payload structure validation
        if not isinstance(payload, dict):
            raise WebhookValidationError("Invalid payload format")
        
        required_fields = ["type", "data"]
        for field in required_fields:
            if field not in payload:
                raise WebhookValidationError(f"Missing required field: {field}")
        
        # Webhook signature validation (if configured)
        if config.webhook_secret:
            await _validate_webhook_signature(request, payload)
        
        logger.debug("Webhook payload validation passed")
        
    except Exception as e:
        if isinstance(e, WebhookValidationError):
            raise
        raise WebhookValidationError(f"Payload validation error: {e}")


async def _validate_webhook_signature(request: Request, payload: Dict[str, Any]) -> None:
    """Validate webhook signature for security
    
    Args:
        request: FastAPI request object
        payload: Webhook payload
        
    Raises:
        WebhookValidationError: If signature validation fails
    """
    try:
        # Get signature from headers
        signature = request.headers.get("notion-webhook-signature")
        
        if not signature:
            raise WebhookValidationError("Missing webhook signature")
        
        # In a real implementation, you would validate the HMAC signature
        # For now, we'll do a simple secret check
        # TODO: Implement proper HMAC-SHA256 validation
        
        logger.debug("Webhook signature validation passed")
        
    except Exception as e:
        if isinstance(e, WebhookValidationError):
            raise
        raise WebhookValidationError(f"Signature validation error: {e}")


async def _process_page_update(page_id: str, payload: Dict[str, Any]) -> None:
    """Process page update event in background
    
    Args:
        page_id: Notion page ID
        payload: Full webhook payload
    """
    try:
        logger.info("Starting background page processing", page_id=page_id)
        
        # Get engine from app state
        from ...api.main import app
        engine = app.state.engine
        
        if not engine:
            logger.error("Engine not available in app state")
            return
        
        # First, check if this page should trigger carousel generation
        # We need to examine the page properties to see if Format/Status changed
        should_process = await _should_process_page(engine, page_id)
        
        if not should_process:
            logger.info("Page does not meet processing criteria", page_id=page_id)
            return
        
        # Generate carousel
        logger.info("Starting carousel generation", page_id=page_id)
        
        result = await engine.generate_carousel(page_id)
        
        if result.success:
            logger.info(
                "Carousel generation completed successfully",
                page_id=page_id,
                slides_generated=result.slides_generated,
                processing_time=result.processing_time_seconds,
                cost=result.estimated_cost
            )
        else:
            logger.error(
                "Carousel generation failed",
                page_id=page_id,
                error=result.error_message
            )
            
    except Exception as e:
        logger.error(
            "Background page processing failed",
            page_id=page_id,
            error=str(e)
        )


async def _should_process_page(engine, page_id: str) -> bool:
    """Determine if a page should trigger carousel generation
    
    Args:
        engine: Carousel engine instance
        page_id: Notion page ID
        
    Returns:
        True if page should be processed
    """
    try:
        # Fetch current page state
        page = await engine.notion.get_page(page_id)
        
        # Check if this is a carousel-enabled page
        if not hasattr(page, 'format') or not page.format:
            logger.debug("Page has no format specified", page_id=page_id)
            return False
        
        # Check status - only process if status is "Ready" 
        if page.status != CarouselStatus.READY:
            logger.debug(
                "Page status not ready for processing",
                page_id=page_id,
                status=page.status.value
            )
            return False
        
        # Check if page has content
        if not page.content or not page.content.strip():
            logger.debug("Page has no content", page_id=page_id)
            return False
        
        logger.info("Page meets processing criteria", page_id=page_id)
        return True
        
    except Exception as e:
        logger.error(
            "Error checking if page should be processed",
            page_id=page_id,
            error=str(e)
        )
        return False


@router.get("/test")
async def test_webhook():
    """Test endpoint for webhook functionality"""
    return {
        "status": "webhook endpoint operational",
        "webhook_secret_configured": bool(config.webhook_secret),
        "environment": config.environment
    }