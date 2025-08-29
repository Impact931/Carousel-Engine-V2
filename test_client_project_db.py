#!/usr/bin/env python3
"""
Test script to check Client Project Database schema and available properties
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from carousel_engine.services.notion import NotionService
from carousel_engine.core.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_client_project_database():
    """Check Client Project Database schema and properties"""
    try:
        # Initialize Notion service
        notion_service = NotionService()
        
        logger.info(f"Checking Client Project Database: {config.client_project_database_id}")
        
        # Query for a few test projects to see structure
        projects = await notion_service.query_client_projects(
            config.client_project_database_id, 
            ""  # Empty search to get any projects
        )
        
        if not projects:
            logger.warning("No projects found in Client Project Database")
            return
        
        # Show first project structure
        first_project = projects[0]
        logger.info(f"Found {len(projects)} projects")
        logger.info(f"First project ID: {first_project.get('id')}")
        
        # Show all available properties
        properties = first_project.get("properties", {})
        logger.info("Available properties in Client Project Database:")
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type", "unknown")
            logger.info(f"  - {prop_name} ({prop_type})")
        
        # Check if our target properties exist
        target_properties = [
            "System_Message_File_ID",
            "System_Message_URL", 
            "System_Message_Generated",
            "Last_System_Message_Update"
        ]
        
        logger.info("Checking for system message properties:")
        for prop_name in target_properties:
            exists = prop_name in properties
            logger.info(f"  - {prop_name}: {'EXISTS' if exists else 'MISSING'}")
        
        return properties
        
    except Exception as e:
        logger.error(f"Error checking Client Project Database: {e}")
        return None

if __name__ == "__main__":
    properties = asyncio.run(check_client_project_database())