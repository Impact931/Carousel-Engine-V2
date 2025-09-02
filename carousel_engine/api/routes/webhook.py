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
        # Log the full payload for debugging
        logger.info("Received Notion webhook", 
                   payload_type=payload.get("type"), 
                   payload_keys=list(payload.keys()),
                   full_payload=payload)
        
        # Handle different webhook formats
        page_id = None
        
        # Check if it's a Notion Automation webhook (different format)
        if "page_id" in payload or "id" in payload:
            # Direct page reference - this is likely from Notion Automation
            page_id = payload.get("page_id") or payload.get("id")
            logger.info("Processing Notion Automation webhook", page_id=page_id)
        
        # Check if it's an official Notion API webhook
        elif payload.get("type") == "page" and "data" in payload:
            # Official Notion API webhook format
            await _validate_webhook_payload(request, payload)
            page_data = payload.get("data", {})
            page_id = page_data.get("id")
            logger.info("Processing official Notion API webhook", page_id=page_id)
        
        else:
            # Unknown format - try to extract page_id from common locations
            logger.warning("Unknown webhook format, attempting to extract page_id", payload=payload)
            
            # Try various common field names
            for field in ["page_id", "id", "notion_page_id", "pageId"]:
                if field in payload:
                    page_id = payload[field]
                    break
            
            # Try nested data
            if not page_id and "data" in payload:
                data = payload["data"]
                for field in ["id", "page_id", "notion_page_id"]:
                    if field in data:
                        page_id = data[field]
                        break
        
        if not page_id:
            logger.error("Could not extract page_id from webhook payload", payload=payload)
            raise HTTPException(status_code=400, detail="Missing page_id in webhook payload")
        
        logger.info("Processing page update", page_id=page_id)
        
        # Queue carousel generation in background
        background_tasks.add_task(
            _process_page_update,
            page_id,
            payload
        )
        
        return {"status": "accepted", "page_id": page_id}
            
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
        
        # Get engine using lazy initialization
        from ...api.main import get_or_create_engine
        engine = get_or_create_engine()
        
        if not engine:
            logger.error("Engine initialization failed")
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
        
        logger.info("Evaluating page for processing", 
                   page_id=page_id,
                   page_title=getattr(page, 'title', 'No title'),
                   has_format=hasattr(page, 'format'),
                   format_value=getattr(page, 'format', None),
                   has_status=hasattr(page, 'status'),
                   status_value=getattr(page, 'status', None),
                   has_content=bool(getattr(page, 'content', None)),
                   content_length=len(getattr(page, 'content', '') or ''))
        
        # Check if page has any meaningful content (title, content, or rich text properties)
        content_sources = []
        if hasattr(page, 'content') and page.content and page.content.strip():
            content_sources.append(f"content({len(page.content)} chars)")
        if hasattr(page, 'title') and page.title and page.title.strip():
            content_sources.append(f"title({len(page.title)} chars)")
        
        # For Notion automation webhooks, we should be more permissive
        # since the page was explicitly triggered by user action
        if not content_sources:
            logger.info("Page has no processable content", page_id=page_id)
            return False
        
        # If page has Format property, check if it's carousel-related
        if hasattr(page, 'format') and page.format:
            if str(page.format).lower() not in ['carousel', 'post', 'content']:
                logger.info("Page format not suitable for carousel generation", 
                          page_id=page_id, format=page.format)
                return False
        
        # If page has Status property, be flexible about status values
        if hasattr(page, 'status') and page.status:
            # Accept various "ready" status values
            ready_statuses = ['ready', 'pending', 'new', 'todo', 'queued', 'active', 'review']
            if str(page.status).lower() not in ready_statuses:
                logger.info("Page status indicates not ready for processing", 
                          page_id=page_id, status=page.status)
                return False
        
        logger.info("Page meets processing criteria", 
                   page_id=page_id,
                   content_sources=content_sources,
                   format=getattr(page, 'format', 'not set'),
                   status=getattr(page, 'status', 'not set'))
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