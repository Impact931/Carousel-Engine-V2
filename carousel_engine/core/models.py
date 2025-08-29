"""
Data models for Carousel Engine v2
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class CarouselFormat(str, Enum):
    """Supported carousel formats"""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram" 
    LINKEDIN = "linkedin"
    IDEA = "idea"
    CAROUSEL = "carousel"
    COMPLETE = "complete"


class CarouselStatus(str, Enum):
    """Carousel processing status"""
    BRAINSTORMING = "brainstorming"
    DRAFT = "draft"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REVIEW = "review"
    ERROR = "error"


class NotionPage(BaseModel):
    """Notion page data model"""
    id: str = Field(..., description="Notion page ID")
    title: str = Field(..., description="Page title")
    content: str = Field(..., description="Rich text content for carousel")
    format: CarouselFormat = Field(..., description="Carousel format")
    status: CarouselStatus = Field(..., description="Processing status")
    google_folder_id: Optional[str] = Field(None, description="Target Google Drive folder ID")
    google_folder_url: Optional[str] = Field(None, description="Generated Google Drive folder URL")
    created_time: datetime = Field(..., description="Page creation timestamp")
    last_edited_time: datetime = Field(..., description="Last edit timestamp")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional Notion properties")


class CarouselSlide(BaseModel):
    """Individual carousel slide"""
    slide_number: int = Field(..., description="Slide position (0 = title slide)")
    title: Optional[str] = Field(None, description="Slide title")
    content: str = Field(..., description="Slide text content")
    background_image_url: Optional[str] = Field(None, description="Generated background image URL")
    is_title_slide: bool = Field(default=False, description="Whether this is the title slide")


class CarouselRequest(BaseModel):
    """Carousel generation request"""
    notion_page_id: str = Field(..., description="Notion page ID to process")
    force_regenerate: bool = Field(default=False, description="Force regeneration even if already processed")


class CarouselResponse(BaseModel):
    """Carousel generation response"""
    success: bool = Field(..., description="Whether generation was successful")
    notion_page_id: str = Field(..., description="Processed Notion page ID")
    slides_generated: int = Field(..., description="Number of slides generated")
    google_drive_folder_url: Optional[str] = Field(None, description="Google Drive folder URL")
    processing_time_seconds: float = Field(..., description="Total processing time")
    estimated_cost: float = Field(..., description="Estimated cost in USD")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class WebhookPayload(BaseModel):
    """Notion webhook payload"""
    object: str = Field(..., description="Webhook object type")
    event_type: str = Field(..., description="Event type (e.g., 'page.updated')")
    event_time: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event data payload")


class CostTracking(BaseModel):
    """Cost tracking for API usage"""
    notion_page_id: str = Field(..., description="Associated Notion page ID")
    openai_cost: float = Field(default=0.0, description="OpenAI API cost")
    google_drive_cost: float = Field(default=0.0, description="Google Drive API cost")
    notion_cost: float = Field(default=0.0, description="Notion API cost")
    total_cost: float = Field(..., description="Total cost for this generation")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Cost tracking timestamp")
    
    
class ProcessingMetrics(BaseModel):
    """Processing performance metrics"""
    notion_page_id: str = Field(..., description="Associated Notion page ID")
    total_processing_time: float = Field(..., description="Total processing time in seconds")
    notion_fetch_time: float = Field(..., description="Time to fetch from Notion")
    content_processing_time: float = Field(..., description="Content processing time")
    image_generation_time: float = Field(..., description="Image generation time")
    google_drive_upload_time: float = Field(..., description="Google Drive upload time")
    notion_update_time: float = Field(..., description="Notion update time")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metrics timestamp")


class ClientDocumentUpload(BaseModel):
    """Client document upload request"""
    project_name: str = Field(..., description="Client project name for matching")
    client_project_id: Optional[str] = Field(None, description="Matched client project ID")
    google_folder_id: Optional[str] = Field(None, description="Created Google Drive folder ID")
    google_folder_url: Optional[str] = Field(None, description="Created Google Drive folder URL")
    documents_uploaded: int = Field(default=0, description="Number of documents successfully uploaded")
    extracted_content: Dict[str, str] = Field(default_factory=dict, description="Extracted document content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")


class DocumentUploadResponse(BaseModel):
    """Document upload response"""
    success: bool = Field(..., description="Upload success status")
    google_folder_url: str = Field(..., description="Google Drive folder URL")
    google_folder_id: str = Field(..., description="Google Drive folder ID")
    project_match_found: bool = Field(..., description="Whether project name was matched")
    matched_project_id: Optional[str] = Field(None, description="Matched Notion project ID")
    matched_project_name: Optional[str] = Field(None, description="Matched Notion project name")
    documents_processed: int = Field(..., description="Number of documents processed")
    system_message_content: str = Field(..., description="Extracted content for system messages")
    system_message_file_id: Optional[str] = Field(None, description="Google Drive system message file ID")
    system_message_url: Optional[str] = Field(None, description="Google Drive system message file URL")
    client_database_updated: bool = Field(default=False, description="Whether Client Project Database was updated")
    processing_time_seconds: float = Field(..., description="Total processing time")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class DocumentType(str, Enum):
    """Document types for client upload"""
    CLIENT_PROFILE = "client_profile"
    CONTENT_ICP = "content_icp" 
    VOICE_STYLE_GUIDE = "voice_style_guide"


class ClientDocument(BaseModel):
    """Individual client document model"""
    document_type: DocumentType = Field(..., description="Type of document")
    filename: str = Field(..., description="Original filename")
    content: str = Field(..., description="Extracted text content")
    file_size_bytes: int = Field(..., description="File size in bytes")
    google_drive_file_id: str = Field(..., description="Google Drive file ID")
    google_drive_file_url: str = Field(..., description="Google Drive file URL")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")