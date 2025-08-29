"""
Carousel Engine v2 - Facebook Carousel Content Automation
Author: Impact Consulting
Version: 2.0.0

A Python application that automates the generation of professional Facebook carousel images
by integrating with Notion for content and Google Drive for image storage.
"""

__version__ = "2.0.0"
__author__ = "Impact Consulting"
__email__ = "support@impactconsulting.com"

from .core.engine import CarouselEngine
from .core.config import Config
from .services.notion import NotionService
from .services.google_drive import GoogleDriveService
from .services.openai_service import OpenAIService

__all__ = [
    "CarouselEngine",
    "Config", 
    "NotionService",
    "GoogleDriveService",
    "OpenAIService"
]