#!/usr/bin/env python3
"""
Test script for Carousel Engine v2
Run a complete carousel generation test locally
"""

import asyncio
import sys
from pathlib import Path

# Add carousel_engine to path
sys.path.insert(0, str(Path(__file__).parent))

from carousel_engine.core.engine import CarouselEngine
from carousel_engine.core.config import config
from carousel_engine.utils.logging import configure_logging


async def test_carousel_generation():
    """Test complete carousel generation workflow"""
    
    print("🎠 Carousel Engine v2 - Local Test")
    print("=" * 50)
    
    # Configure logging
    configure_logging(level="INFO", format_json=False)
    
    try:
        # Initialize engine
        print("🔧 Initializing Carousel Engine...")
        engine = CarouselEngine()
        
        # Health check
        print("🏥 Performing health check...")
        health_status = await engine.health_check()
        
        print(f"Engine Status: {health_status['engine']}")
        for service, status in health_status['services'].items():
            print(f"  {service}: {status}")
        
        if "unhealthy" in health_status['engine']:
            print("❌ Some services are unhealthy. Please check your configuration.")
            return False
        
        # Test with the most recent Brainstorming carousel from the database
        print("\n🔍 Finding Carousel records with Brainstorming status...")
        
        # Query the database to get brainstorming carousels
        from carousel_engine.services.notion import NotionService
        notion_service = NotionService()
        
        # Get brainstorming carousel pages from the database
        brainstorming_pages = await notion_service.query_brainstorming_carousels(config.notion_database_id, limit=5)
        
        if not brainstorming_pages:
            print("❌ No Carousel records with Brainstorming status found in the database.")
            print("   Please create a record with Format='Carousel' and Status='Brainstorming'")
            return False
        
        # Use the first page (most recent brainstorming carousel)
        test_page_id = brainstorming_pages[0]["id"]
        
        # Extract title more safely
        page_title = "Untitled"
        try:
            properties = brainstorming_pages[0].get("properties", {})
            # Find the title property (could be named differently)
            for key, prop in properties.items():
                if prop.get("type") == "title" and prop.get("title"):
                    page_title = "".join([part.get("plain_text", "") for part in prop["title"]])
                    break
        except Exception as e:
            print(f"⚠️  Could not extract page title: {e}")
        
        print(f"📄 Selected brainstorming carousel: {page_title}")
        print(f"🆔 Page ID: {test_page_id}")
        print(f"📊 Total brainstorming carousels found: {len(brainstorming_pages)}")
        
        print(f"\n🚀 Starting carousel generation for brainstorming record: {test_page_id}")
        print("This may take 30-60 seconds...")
        
        # Generate carousel
        result = await engine.generate_carousel(test_page_id, force_regenerate=True)
        
        # Display results
        print("\n" + "=" * 50)
        print("📊 GENERATION RESULTS")
        print("=" * 50)
        
        if result.success:
            print("✅ SUCCESS!")
            print(f"📄 Page ID: {result.notion_page_id}")
            print(f"🖼️  Slides Generated: {result.slides_generated}")
            print(f"⏱️  Processing Time: {result.processing_time_seconds:.2f} seconds")
            print(f"💰 Estimated Cost: ${result.estimated_cost:.4f}")
            
            if result.google_drive_folder_url:
                print(f"📁 Google Drive Folder: {result.google_drive_folder_url}")
            
            # Get metrics
            metrics = engine.get_processing_metrics(test_page_id)
            if metrics:
                print(f"\n📈 DETAILED METRICS:")
                print(f"  Notion fetch: {metrics.notion_fetch_time:.2f}s")
                print(f"  Content processing: {metrics.content_processing_time:.2f}s")
                print(f"  Image generation: {metrics.image_generation_time:.2f}s")
                print(f"  Google Drive upload: {metrics.google_drive_upload_time:.2f}s")
                print(f"  Notion update: {metrics.notion_update_time:.2f}s")
            
            print(f"\n🎉 Carousel generation completed successfully!")
            return True
        else:
            print("❌ FAILED!")
            print(f"Error: {result.error_message}")
            print(f"Processing Time: {result.processing_time_seconds:.2f} seconds")
            print(f"Estimated Cost: ${result.estimated_cost:.4f}")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 Test cancelled by user")
        return False
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return False


def check_environment():
    """Check if required environment variables are set"""
    print("🔍 Checking environment configuration...")
    
    required_vars = [
        "NOTION_API_KEY",
        "GOOGLE_OAUTH_CLIENT_ID", 
        "OPENAI_API_KEY",
        "NOTION_DATABASE_ID"
    ]
    
    missing_vars = []
    
    for var in required_vars:
        try:
            value = getattr(config, var.lower())
            if value:
                print(f"  ✅ {var}: configured")
            else:
                missing_vars.append(var)
                print(f"  ❌ {var}: missing")
        except:
            missing_vars.append(var)
            print(f"  ❌ {var}: missing")
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file before testing.")
        return False
    
    print("✅ All required environment variables are configured")
    return True


if __name__ == "__main__":
    print("🎠 Carousel Engine v2 - Local Test Runner")
    print("=" * 50)
    
    # Check environment first
    if not check_environment():
        sys.exit(1)
    
    # Run test
    success = asyncio.run(test_carousel_generation())
    
    if success:
        print("\n🎉 Test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Test failed. Check the error messages above.")
        sys.exit(1)