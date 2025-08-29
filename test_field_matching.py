#!/usr/bin/env python3
"""
Test script to verify Project field matching and GPT-4o integration
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_field_matching():
    """Test the corrected field matching logic"""
    try:
        # Initialize Notion service
        notion_service = NotionService()
        
        logger.info("=== Testing Field Matching Logic ===")
        
        # First, get all records to examine their fields
        all_pages = await notion_service.query_database(
            config.notion_database_id,
            limit=5
        )
        
        # Show all pages and their formats
        logger.info(f"Found {len(all_pages)} total pages in Content Engine database")
        carousel_pages = []
        
        for i, page in enumerate(all_pages):
            page_id = page.get("id")
            properties = page.get("properties", {})
            title = notion_service._extract_title(page) or "Untitled"
            format_prop = notion_service._get_property_value(properties, "Format", "")
            status_prop = notion_service._get_property_value(properties, "Status", "")
            
            logger.info(f"Page {i+1}: '{title}' - Format: '{format_prop}' - Status: '{status_prop}'")
            
            if format_prop and "carousel" in format_prop.lower():
                carousel_pages.append(page)
        
        logger.info(f"Found {len(carousel_pages)} pages with Carousel format")
        
        if not carousel_pages:
            logger.warning("No Carousel format records found - will test with first available page")
            if all_pages:
                carousel_pages = [all_pages[0]]  # Use first page for testing
        
        logger.info(f"Found {len(carousel_pages)} Carousel records")
        
        for i, page in enumerate(carousel_pages):
            page_id = page.get("id")
            properties = page.get("properties", {})
            title = notion_service._extract_title(page) or "Untitled"
            
            logger.info(f"\n--- Carousel Record {i+1}: {title} ---")
            logger.info(f"Page ID: {page_id}")
            
            # Check if Project field exists and what type it is
            project_field = properties.get("Project", {})
            if project_field:
                project_type = project_field.get("type", "unknown")
                logger.info(f"Project field found - Type: {project_type}")
                
                # Extract value based on type
                if project_type == "relation":
                    relations = project_field.get("relation", [])
                    logger.info(f"Project relations: {len(relations)} linked pages")
                    for rel in relations:
                        rel_id = rel.get("id")
                        logger.info(f"  - Related page ID: {rel_id}")
                        
                elif project_type == "select":
                    select = project_field.get("select")
                    if select:
                        logger.info(f"Project select value: {select.get('name')}")
                    else:
                        logger.info("Project select field is empty")
                        
                elif project_type == "rich_text":
                    rich_text = project_field.get("rich_text", [])
                    text_value = "".join([part.get("plain_text", "") for part in rich_text])
                    logger.info(f"Project rich_text value: '{text_value}'")
                    
                else:
                    logger.info(f"Project field type '{project_type}' - Raw value: {project_field}")
            else:
                logger.warning("No Project field found in this carousel record")
                
            # List all available fields for reference
            logger.info("All available fields:")
            for field_name in properties.keys():
                field_type = properties[field_name].get("type", "unknown")
                logger.info(f"  - {field_name} ({field_type})")
        
        # Test Client Project Database query
        logger.info(f"\n=== Testing Client Project Database Query ===")
        
        # Try querying with a test project name
        test_project_name = "jhr studio"  # Based on our uploaded documents
        logger.info(f"Testing query for: '{test_project_name}'")
        
        matching_projects = await notion_service.query_client_projects(
            config.client_project_database_id,
            test_project_name
        )
        
        logger.info(f"Found {len(matching_projects)} matching projects")
        
        for i, project in enumerate(matching_projects):
            project_id = project.get("id")
            properties = project.get("properties", {})
            
            logger.info(f"\nClient Project {i+1}: {project_id}")
            
            # Check relevant fields
            client_project_name = notion_service._get_property_value(properties, "Client_Project_Name", "")
            system_message_url = notion_service._get_property_value(properties, "System_Message_URL", "")
            system_message_generated = notion_service._get_property_value(properties, "System_Message_Generated", False)
            
            logger.info(f"  Client_Project_Name: '{client_project_name}'")
            logger.info(f"  System_Message_URL: {system_message_url}")
            logger.info(f"  System_Message_Generated: {system_message_generated}")
        
    except Exception as e:
        logger.error(f"Error in field matching test: {e}")

if __name__ == "__main__":
    asyncio.run(test_field_matching())