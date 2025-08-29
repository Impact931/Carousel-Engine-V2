#!/usr/bin/env python3
"""
Test script to verify system message usage in content generation
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from carousel_engine.services.notion import NotionService
from carousel_engine.services.google_drive import GoogleDriveService
from carousel_engine.core.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_system_message_usage():
    """Verify that the system message was properly used in content generation"""
    try:
        logger.info("=== Verifying System Message Usage ===")
        
        # Initialize services
        notion_service = NotionService()
        google_drive_service = GoogleDriveService()
        
        # 1. Get the Penfield Realty Project from Client Project Database
        logger.info("Step 1: Retrieving Penfield Realty Project system message...")
        
        matching_projects = await notion_service.query_client_projects(
            config.client_project_database_id,
            "Penfield Realty Project"
        )
        
        if not matching_projects:
            logger.error("Penfield Realty Project not found in Client Project Database")
            return
        
        project = matching_projects[0]
        properties = project.get("properties", {})
        
        # Get system message details
        system_message_url = notion_service._get_property_value(properties, "System_Message_URL", "")
        system_message_generated = notion_service._get_property_value(properties, "System_Message_Generated", False)
        
        logger.info(f"System Message URL: {system_message_url}")
        logger.info(f"System Message Generated: {system_message_generated}")
        
        if not system_message_url or not system_message_generated:
            logger.error("No system message found for Penfield Realty Project")
            return
        
        # 2. Download and examine the system message content
        logger.info("Step 2: Downloading system message content...")
        
        # Extract file ID from Google Drive URL
        if "drive.google.com" in system_message_url and "/file/d/" in system_message_url:
            file_id = system_message_url.split("/file/d/")[1].split("/")[0]
            
            # Download system message
            system_message_content = await google_drive_service.download_text_file(file_id)
            
            logger.info(f"System message length: {len(system_message_content)} characters")
            
            # Show key parts of the system message
            lines = system_message_content.split('\n')
            logger.info("System message preview (first 10 lines):")
            for i, line in enumerate(lines[:10]):
                if line.strip():
                    logger.info(f"  {i+1}: {line.strip()}")
            
            # Look for key client-specific elements
            key_indicators = [
                "Tiffany", "Penfield", "real estate", "agent", "client profile",
                "voice", "style", "brand", "ICP", "target audience"
            ]
            
            found_indicators = []
            for indicator in key_indicators:
                if indicator.lower() in system_message_content.lower():
                    found_indicators.append(indicator)
            
            logger.info(f"Found client-specific indicators: {found_indicators}")
            
            # 3. Find the actual Carousel format record that should use this system message
            logger.info("Step 3: Finding Carousel format records...")
            
            all_pages = await notion_service.query_database(
                config.notion_database_id,
                limit=50
            )
            
            carousel_records = []
            for page in all_pages:
                properties = page.get("properties", {})
                format_prop = notion_service._get_property_value(properties, "Format", "")
                
                if format_prop and format_prop.lower() == "carousel":
                    title = notion_service._extract_title(page) or "Untitled"
                    page_id = page.get("id")
                    carousel_records.append((page_id, title, page))
                    logger.info(f"Found Carousel record: '{title}' (ID: {page_id})")
            
            if not carousel_records:
                logger.warning("No Carousel format records found")
                return
            
            # 4. Check if the carousel records are linked to Penfield Realty Project
            logger.info("Step 4: Checking Project relations...")
            
            for page_id, title, page in carousel_records:
                properties = page.get("properties", {})
                project_field = properties.get("Project", {})
                
                if project_field.get("type") == "relation":
                    relations = project_field.get("relation", [])
                    for relation in relations:
                        related_page_id = relation.get("id")
                        if related_page_id:
                            # Get the related project name
                            related_page = notion_service.client.pages.retrieve(page_id=related_page_id)
                            project_name = notion_service._extract_title(related_page)
                            logger.info(f"Carousel '{title}' is linked to project: '{project_name}'")
                            
                            if project_name == "Penfield Realty Project":
                                logger.info(f"✅ FOUND MATCH: Carousel '{title}' should use Penfield system message")
                                return page_id, title, system_message_content
            
            logger.warning("No Carousel records found linked to Penfield Realty Project")
            
        else:
            logger.error("Invalid system message URL format")
            
    except Exception as e:
        logger.error(f"Error verifying system message usage: {e}")

if __name__ == "__main__":
    asyncio.run(verify_system_message_usage())