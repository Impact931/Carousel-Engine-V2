#!/usr/bin/env python3
"""
Test script to simulate webhook trigger for Carousel format record
"""

import asyncio
import logging
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from carousel_engine.services.notion import NotionService
from carousel_engine.core.config import config
from carousel_engine.core.engine import CarouselEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def find_carousel_records():
    """Find Carousel format records to test with"""
    try:
        # Initialize Notion service
        notion_service = NotionService()
        
        logger.info("Searching for Carousel format records...")
        
        # Query for all records to find Carousel format specifically
        all_pages = await notion_service.query_database(
            config.notion_database_id,
            limit=50  # Increase limit to find all records
        )
        
        logger.info(f"Found {len(all_pages)} total records")
        
        # Look specifically for Carousel format pages
        carousel_pages = []
        test_pages = []
        
        for page in all_pages:
            properties = page.get("properties", {})
            format_prop = notion_service._get_property_value(properties, "Format", "")
            project_field = properties.get("Project", {})
            
            # Prioritize actual Carousel format records
            if format_prop and format_prop.lower() == "carousel":
                carousel_pages.append(page)
                logger.info(f"Found CAROUSEL format record: {notion_service._extract_title(page) or 'Untitled'}")
            
            # Keep pages with Project relations as backup
            if project_field.get("type") == "relation" and project_field.get("relation"):
                test_pages.append(page)
        
        # Use Carousel format records if available, otherwise use pages with Project relations
        if carousel_pages:
            test_pages = carousel_pages
            logger.info(f"Using {len(carousel_pages)} Carousel format records for testing")
        else:
            logger.warning("No Carousel format records found, using pages with Project relations")
        
        logger.info(f"Found {len(test_pages)} pages with Project relations")
        
        for i, page in enumerate(test_pages):
            page_id = page.get("id")
            properties = page.get("properties", {})
            
            # Extract title and status
            title = notion_service._extract_title(page) or "Untitled"
            status_prop = notion_service._get_property_value(properties, "Status", "Unknown")
            format_prop = notion_service._get_property_value(properties, "Format", "Unknown")
            
            logger.info(f"  {i+1}. {title[:60]}... (ID: {page_id}, Format: {format_prop}, Status: {status_prop})")
        
        return test_pages
        
    except Exception as e:
        logger.error(f"Error finding carousel records: {e}")
        return []

async def simulate_webhook_trigger(page_id: str):
    """Simulate a webhook trigger for a specific carousel page"""
    try:
        logger.info(f"Simulating webhook trigger for page: {page_id}")
        
        # Initialize the Carousel Engine
        engine = CarouselEngine()
        
        logger.info("Triggering carousel generation...")
        
        # Generate the carousel (this should now use client system message if available)
        response = await engine.generate_carousel(
            notion_page_id=page_id,
            force_regenerate=True  # Force regeneration to test system message integration
        )
        
        logger.info(f"Carousel generation completed!")
        logger.info(f"Success: {response.success}")
        logger.info(f"Slides generated: {response.slides_generated}")
        logger.info(f"Processing time: {response.processing_time_seconds:.2f}s")
        logger.info(f"Google Drive URL: {response.google_drive_folder_url}")
        
        if response.error_message:
            logger.error(f"Error: {response.error_message}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error simulating webhook trigger: {e}")
        return None

async def test_carousel_webhook_simulation():
    """Main test function"""
    try:
        logger.info("=== Testing Carousel Webhook Simulation ===")
        
        # Find available records with Project relations
        test_records = await find_carousel_records()
        
        if not test_records:
            logger.warning("No records with Project relations found to test with")
            return
        
        # Use the first record with Project relation for testing
        test_page = test_records[0]
        page_id = test_page.get("id")
        
        logger.info(f"Using carousel record: {page_id}")
        
        # Simulate webhook trigger
        response = await simulate_webhook_trigger(page_id)
        
        if response and response.success:
            logger.info("✅ Carousel webhook simulation successful!")
            logger.info("🎯 System message integration should be active in generated content")
        else:
            logger.error("❌ Carousel webhook simulation failed")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_carousel_webhook_simulation())