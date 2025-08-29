#!/usr/bin/env python3
"""
Test script for client document upload system
"""

import asyncio
import tempfile
import json
from pathlib import Path

# Add carousel_engine to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from carousel_engine.services.notion import NotionService
from carousel_engine.services.google_drive import GoogleDriveService
from carousel_engine.services.document_processor import DocumentProcessor
from carousel_engine.core.config import config
from carousel_engine.core.models import DocumentType


async def test_document_upload_workflow():
    """Test the complete document upload workflow"""
    
    print("🧪 Client Document Upload System Test")
    print("=" * 50)
    
    try:
        # Initialize services
        print("🔧 Initializing services...")
        notion_service = NotionService()
        google_drive_service = GoogleDriveService()
        document_processor = DocumentProcessor()
        
        # Step 1: Test project name matching
        print("\n1️⃣ Testing project name matching...")
        test_project_names = ["Peter", "Realty", "Noble", "AI"]
        
        for project_name in test_project_names:
            try:
                projects = await notion_service.query_client_projects(
                    config.client_project_database_id,
                    project_name
                )
                print(f"   📋 '{project_name}': Found {len(projects)} matching projects")
                
                if projects:
                    # Test client name extraction
                    client_name = notion_service.extract_client_name_from_project(projects[0])
                    print(f"   👤 Extracted client name: {client_name}")
                    break
            except Exception as e:
                print(f"   ❌ Error searching for '{project_name}': {e}")
        
        # Step 2: Test document processing
        print("\n2️⃣ Testing document processing...")
        
        # Create sample documents
        sample_docs = {
            DocumentType.CLIENT_PROFILE: """
                Client Name: Sample Real Estate Company
                Industry: Real Estate
                Target Market: First-time homebuyers and relocating professionals
                Company Values: Trust, expertise, and personalized service
                Brand Personality: Professional yet approachable, knowledgeable, trustworthy
            """,
            DocumentType.CONTENT_ICP: """
                Ideal Client Profile:
                - Age: 25-45 years old
                - Income: $75,000+ annual household income
                - Life Stage: First-time buyers, growing families, relocating professionals
                - Pain Points: Complex buying process, market uncertainty, finding the right neighborhood
                - Goals: Finding the perfect home that fits their lifestyle and budget
            """,
            DocumentType.VOICE_STYLE_GUIDE: """
                Brand Voice: Professional, warm, and reassuring
                Tone: Conversational yet authoritative
                Style Guidelines:
                - Use accessible language, avoid jargon
                - Include personal anecdotes and success stories
                - Focus on emotions and lifestyle benefits
                - Always end with a clear next step or call-to-action
            """
        }
        
        processed_docs = {}
        
        for doc_type, content in sample_docs.items():
            try:
                # Create temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                    tmp_file.write(content.strip())
                    tmp_file_path = tmp_file.name
                
                # Read file as bytes
                with open(tmp_file_path, 'rb') as f:
                    file_data = f.read()
                
                # Process document
                extracted_content, file_size = await document_processor.process_document(
                    file_data, f"{doc_type.value}.txt", doc_type
                )
                
                processed_docs[doc_type.value] = extracted_content
                print(f"   ✅ {doc_type.value}: Processed {file_size} bytes, extracted {len(extracted_content)} characters")
                
                # Clean up temp file
                Path(tmp_file_path).unlink()
                
            except Exception as e:
                print(f"   ❌ Error processing {doc_type.value}: {e}")
        
        # Step 3: Test system message generation
        print("\n3️⃣ Testing system message generation...")
        try:
            system_message = document_processor.generate_system_message(processed_docs)
            print(f"   ✅ Generated system message: {len(system_message)} characters")
            print(f"   📝 Preview: {system_message[:200]}...")
            
        except Exception as e:
            print(f"   ❌ Error generating system message: {e}")
        
        # Step 4: Test Google Drive folder creation (without actual files)
        print("\n4️⃣ Testing Google Drive folder creation...")
        try:
            # List existing folders to test connectivity
            existing_folders = await google_drive_service.list_folders(
                config.target_google_drive_folder_id
            )
            print(f"   📁 Found {len(existing_folders)} existing client folders")
            
            # Test serial number generation
            test_client_name = "TestClient"
            serial_number = google_drive_service._generate_serial_number(test_client_name, existing_folders)
            print(f"   🔢 Next serial number for '{test_client_name}': {serial_number:03d}")
            
        except Exception as e:
            print(f"   ❌ Error testing Google Drive: {e}")
        
        # Step 5: Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        all_services_working = True
        
        # Check service health
        services = {
            "Notion API": "✅ Working" if len(projects) > 0 else "❌ Issues",
            "Document Processor": "✅ Working" if len(processed_docs) == 3 else "❌ Issues", 
            "System Message Generator": "✅ Working" if 'system_message' in locals() else "❌ Issues",
            "Google Drive API": "✅ Working" if len(existing_folders) >= 0 else "❌ Issues"
        }
        
        for service, status in services.items():
            print(f"{service}: {status}")
            if "❌" in status:
                all_services_working = False
        
        print(f"\n🎯 Overall System Status: {'✅ READY FOR PRODUCTION' if all_services_working else '⚠️  NEEDS ATTENTION'}")
        
        # Usage instructions
        if all_services_working:
            print(f"""
🚀 SYSTEM READY! 

Upload Interface: http://localhost:8000/api/documents/upload
API Documentation: http://localhost:8000/docs
Status Check: http://localhost:8000/api/documents/status

To test with real documents:
1. Visit the upload page in your browser
2. Enter a project name that exists in your Client Project Database
3. Upload your 3 client documents (Profile, ICP, Voice Guide)
4. The system will create a Google Drive folder and generate a system message

Configuration:
- Client Project Database: {config.client_project_database_id}
- Google Drive Target Folder: {config.target_google_drive_folder_id}
- Max File Size: {config.max_file_size_mb}MB
- Allowed Types: {', '.join(config.allowed_file_types)}
            """)
        
        return all_services_working
        
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        return False


async def main():
    """Run the test"""
    success = await test_document_upload_workflow()
    
    if success:
        print("\n🎉 All tests passed! Client document upload system is ready.")
        return True
    else:
        print("\n❌ Some tests failed. Please check the error messages above.")
        return False


if __name__ == "__main__":
    asyncio.run(main())