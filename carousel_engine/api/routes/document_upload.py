"""
Document upload API routes for client documents
"""

import logging
import re
import time
from typing import Dict, List, Tuple
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from ...core.config import config
from ...core.models import DocumentUploadResponse, DocumentType, ClientDocument
from ...services.notion import NotionService
from ...services.google_drive import GoogleDriveService
from ...services.document_processor import DocumentProcessor
from ...core.exceptions import (
    NotionAPIError, 
    GoogleDriveError, 
    ContentProcessingError
)

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/documents", tags=["document-upload"])

# Initialize templates (will create template files later)
templates = Jinja2Templates(directory="carousel_engine/static/templates")


def extract_google_drive_folder_id(drive_url: str) -> str:
    """Extract folder ID from Google Drive share URL
    
    Args:
        drive_url: Google Drive folder share URL
        
    Returns:
        Extracted folder ID
        
    Raises:
        ValueError: If URL format is invalid
    """
    # Common Google Drive folder URL patterns:
    # https://drive.google.com/drive/folders/FOLDER_ID
    # https://drive.google.com/drive/folders/FOLDER_ID?usp=sharing
    # https://drive.google.com/drive/u/0/folders/FOLDER_ID
    
    patterns = [
        r'https://drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)',
        r'https://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, drive_url)
        if match:
            return match.group(1)
    
    raise ValueError(f"Invalid Google Drive folder URL format: {drive_url}")


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Serve the document upload page
    
    Returns:
        HTML upload form
    """
    return templates.TemplateResponse(
        "upload.html", 
        {
            "request": request,
            "max_file_size_mb": config.max_file_size_mb,
            "allowed_types": ", ".join(config.allowed_file_types)
        }
    )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_client_documents(
    project_name: str = Form(..., description="Client project name for matching"),
    google_drive_folder: str = Form(..., description="Google Drive folder URL for this client"),
    client_profile: UploadFile = File(..., description="Client profile document"),
    content_icp: UploadFile = File(..., description="Content ideal client profile document"),
    voice_style_guide: UploadFile = File(..., description="Voice and style guide document"),
):
    """Upload client documents and create system message
    
    Args:
        project_name: Client project name to match in database
        google_drive_folder: Google Drive folder URL for this client
        client_profile: Client profile document file
        content_icp: Content ideal client profile document file  
        voice_style_guide: Voice and style guide document file
        
    Returns:
        DocumentUploadResponse with upload results and system message content
        
    Raises:
        HTTPException: If upload fails
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting client document upload for project: {project_name}")
        
        # Extract Google Drive folder ID from URL
        try:
            target_folder_id = extract_google_drive_folder_id(google_drive_folder)
            logger.info(f"Extracted folder ID: {target_folder_id} from URL: {google_drive_folder}")
        except ValueError as e:
            logger.error(f"Invalid Google Drive folder URL: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        
        # Initialize services
        notion_service = NotionService()
        google_drive_service = GoogleDriveService()
        document_processor = DocumentProcessor()
        
        # Collect uploaded files
        uploaded_files = [
            (client_profile, DocumentType.CLIENT_PROFILE),
            (content_icp, DocumentType.CONTENT_ICP),
            (voice_style_guide, DocumentType.VOICE_STYLE_GUIDE)
        ]
        
        # Validate all files
        for file, doc_type in uploaded_files:
            file_size = 0
            if hasattr(file, 'size') and file.size:
                file_size = file.size
            else:
                # Read file to get size if not available
                content = await file.read()
                file_size = len(content)
                await file.seek(0)  # Reset file pointer
            
            is_valid, error_message = document_processor.validate_file_upload(
                file.filename, file_size
            )
            if not is_valid:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid file {file.filename}: {error_message}"
                )
        
        # Step 1: Match project name in Client Project Database
        logger.info("Searching for matching client project...")
        matching_projects = await notion_service.query_client_projects(
            config.client_project_database_id, 
            project_name
        )
        
        if not matching_projects:
            logger.error(f"No existing client project found for '{project_name}' - cannot proceed")
            raise HTTPException(
                status_code=404,
                detail=f"Client project '{project_name}' not found in database. Please ensure the project exists before uploading documents."
            )
        
        # Use the first matching project
        matched_project = matching_projects[0]
        matched_project_id = matched_project.get("id")
        
        # Extract client name from project
        client_name = notion_service.extract_client_name_from_project(matched_project)
        logger.info(f"Matched project ID: {matched_project_id}, Client: {client_name}")
        
        # Step 2: Create Google Drive folder with client name + serial number
        logger.info(f"Creating Google Drive folder for client: {client_name}")
        folder_id, folder_url = await google_drive_service.create_client_folder(
            client_name, 
            target_folder_id
        )
        
        # Step 3: Process and upload documents
        logger.info("Processing and uploading client documents...")
        processed_documents: List[ClientDocument] = []
        extracted_content: Dict[str, str] = {}
        
        documents_to_upload = []
        
        for file, doc_type in uploaded_files:
            # Read file content
            file_content = await file.read()
            
            # Process document and extract content
            content, file_size = await document_processor.process_document(
                file_content, file.filename, doc_type
            )
            
            # Store extracted content for system message generation
            extracted_content[doc_type.value] = content
            
            # Prepare for Google Drive upload
            mime_type = google_drive_service._get_mime_type(file.filename)
            documents_to_upload.append((file_content, file.filename, mime_type))
            
            logger.info(f"Successfully processed {doc_type.value}: {file.filename}")
        
        # Upload all documents to Google Drive
        upload_results = await google_drive_service.upload_client_documents(
            documents_to_upload, folder_id
        )
        
        # Create ClientDocument objects
        for i, (file, doc_type) in enumerate(uploaded_files):
            file_content = await file.read()  # Re-read for size calculation
            file_id, file_url = upload_results[i]
            
            client_doc = ClientDocument(
                document_type=doc_type,
                filename=file.filename,
                content=extracted_content[doc_type.value],
                file_size_bytes=len(file_content),
                google_drive_file_id=file_id,
                google_drive_file_url=file_url
            )
            processed_documents.append(client_doc)
        
        # Step 4: Generate system message from extracted content
        logger.info("Generating system message from extracted content...")
        system_message = document_processor.generate_system_message(extracted_content)
        
        # Step 5: Save system message to Google Drive
        logger.info("Uploading system message to Google Drive...")
        system_message_file_id, system_message_url = await google_drive_service.upload_system_message(
            system_message, client_name, folder_id
        )
        
        # Step 6: Update Client Project Database with system message references
        logger.info("Updating Client Project Database with system message references...")
        await notion_service.update_client_project_system_message(
            matched_project_id, system_message_file_id, system_message_url, client_name
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        logger.info(f"Successfully completed document upload with system message in {processing_time:.2f}s")
        
        # Return success response
        return DocumentUploadResponse(
            success=True,
            google_folder_url=folder_url,
            google_folder_id=folder_id,
            project_match_found=True,
            matched_project_id=matched_project_id,
            matched_project_name=client_name,
            documents_processed=len(processed_documents),
            system_message_content=system_message,
            system_message_file_id=system_message_file_id,
            system_message_url=system_message_url,
            client_database_updated=True,
            processing_time_seconds=processing_time
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except NotionAPIError as e:
        logger.error(f"Notion API error during document upload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to access Notion database: {e.message}"
        )
    except GoogleDriveError as e:
        logger.error(f"Google Drive error during document upload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload documents to Google Drive: {e.message}"
        )
    except ContentProcessingError as e:
        logger.error(f"Document processing error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process uploaded documents: {e.message}"
        )
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Unexpected error during document upload: {e}")
        
        return DocumentUploadResponse(
            success=False,
            google_folder_url="",
            google_folder_id="",
            project_match_found=False,
            documents_processed=0,
            system_message_content="",
            processing_time_seconds=processing_time,
            error_message=f"Unexpected error: {str(e)}"
        )


@router.get("/test")
async def test_upload_endpoint():
    """Test endpoint to verify document upload API is working
    
    Returns:
        Status message
    """
    return {
        "status": "ok",
        "message": "Document upload API is working",
        "config": {
            "max_file_size_mb": config.max_file_size_mb,
            "allowed_file_types": config.allowed_file_types,
            "client_project_database_id": config.client_project_database_id,
            "note": "Google Drive folder ID is now provided per upload request"
        }
    }


@router.get("/status")
async def upload_service_status():
    """Check status of upload service dependencies
    
    Returns:
        Service health status
    """
    try:
        # Initialize services to test connectivity
        notion_service = NotionService()
        google_drive_service = GoogleDriveService()
        document_processor = DocumentProcessor()
        
        # Test basic operations
        status = {
            "notion": "unknown",
            "google_drive": "unknown", 
            "document_processor": "ok"
        }
        
        # Test Notion connection
        try:
            # Try to query the client project database (limit to 1 for quick test)
            # Use a simple query without sorts to test basic connectivity
            query_params = {
                "database_id": config.client_project_database_id,
                "page_size": 1
            }
            response = notion_service.client.databases.query(**query_params)
            status["notion"] = "ok"
        except Exception as e:
            status["notion"] = f"error: {str(e)}"
        
        # Test Google Drive connection
        try:
            # Try to get folder info for target location
            folder_info = await google_drive_service.get_folder_info(config.target_google_drive_folder_id)
            status["google_drive"] = "ok" if folder_info else "folder_not_found"
        except Exception as e:
            status["google_drive"] = f"error: {str(e)}"
        
        return {
            "overall_status": "ok" if all("error" not in str(v) for v in status.values()) else "error",
            "services": status,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error checking upload service status: {e}")
        return {
            "overall_status": "error",
            "error": str(e),
            "timestamp": time.time()
        }