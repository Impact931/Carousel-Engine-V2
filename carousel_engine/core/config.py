"""
Configuration management for Carousel Engine v2
"""

import os
from typing import Optional, List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application configuration with validation"""
    
    # Application Settings
    app_name: str = Field(default="Carousel Engine v2", description="Application name")
    version: str = Field(default="2.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="production", description="Environment")
    
    # API Keys - Made optional for serverless compatibility
    notion_api_key: Optional[str] = Field(default=None, description="Notion API integration token")
    google_oauth_client_id: Optional[str] = Field(default=None, description="Google OAuth client ID")
    google_oauth_client_secret: Optional[str] = Field(default=None, description="Google OAuth client secret")
    google_refresh_token: Optional[str] = Field(default=None, description="Google OAuth refresh token")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for image generation")
    
    # Database & Content - Made optional for serverless compatibility
    notion_database_id: Optional[str] = Field(default=None, description="Notion database ID for content")
    
    # Image Generation Settings
    image_width: int = Field(default=1080, description="Generated image width in pixels")
    image_height: int = Field(default=1080, description="Generated image height in pixels") 
    max_carousel_slides: int = Field(default=7, description="Maximum number of slides per carousel")
    lines_per_slide: int = Field(default=2, description="Maximum lines of text per slide")
    
    # Font Settings for Maximum Legibility
    min_title_font_size: int = Field(default=60, description="Minimum font size for titles (pt)")
    max_title_font_size: int = Field(default=96, description="Maximum font size for titles (pt)")
    min_content_font_size: int = Field(default=60, description="Minimum font size for content (pt)")
    max_content_font_size: int = Field(default=84, description="Maximum font size for content (pt)")
    
    # Cost Monitoring
    max_cost_per_run: float = Field(default=1.00, description="Maximum cost per carousel generation")
    
    # Google Drive Settings
    google_drive_folder_name: str = Field(default="Carousel Images", description="Default folder name")
    
    # Webhook Settings
    webhook_secret: Optional[str] = Field(default=None, description="Notion webhook verification secret")
    
    # Client Document Upload Settings
    client_project_database_id: str = Field(default="231c2a32df0d8174a3f9fcdf5be1a0d8", description="Client Project Database ID")
    social_media_dashboard_page_id: str = Field(default="Social-Media-231c2a32df0d81c485fef840c3d38ff3", description="Social Media Dashboard Page ID")
    target_google_drive_folder_id: str = Field(default="1lalsBxSRqiblOMF1_r76OEbI4eEvPJuq", description="Target Google Drive Location")
    max_file_size_mb: int = Field(default=10, description="Maximum file size in MB")
    allowed_file_types: Union[List[str], str] = Field(default=["pdf", "docx", "txt", "md"], description="Allowed document types")
    
    @field_validator('allowed_file_types')
    @classmethod
    def parse_file_types(cls, v):
        """Convert comma-separated string to list if needed"""
        if isinstance(v, str):
            return [item.strip() for item in v.split(',') if item.strip()]
        return v
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    
    # Context7 MCP Configuration
    context7_api_key: Optional[str] = Field(default=None, description="Context7 MCP API key")
    
    # Legacy project variables (for template compatibility)
    database_url: Optional[str] = Field(default=None, description="Database URL")
    api_base_url: Optional[str] = Field(default="https://api.yourproject.com", description="API base URL")
    api_key: Optional[str] = Field(default=None, description="General API key")
    node_env: Optional[str] = Field(default="development", description="Node.js environment")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() in ("development", "dev", "local")
        
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() in ("production", "prod")
    
    def validate_required_for_carousel_generation(self) -> bool:
        """Validate that required fields are available for carousel generation"""
        required_fields = {
            'notion_api_key': self.notion_api_key,
            'notion_database_id': self.notion_database_id,
            'openai_api_key': self.openai_api_key
        }
        
        missing = [field for field, value in required_fields.items() if not value]
        if missing:
            return False, f"Missing required configuration: {', '.join(missing)}"
        
        return True, "All required configuration present"
    
    def validate_required_for_google_drive(self) -> bool:
        """Validate that required fields are available for Google Drive operations"""
        if not self.google_oauth_client_id or not self.google_oauth_client_secret:
            return False, "Missing Google OAuth credentials"
        return True, "Google Drive configuration present"


# Global config instance
config = Config()