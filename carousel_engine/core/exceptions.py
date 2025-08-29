"""
Custom exceptions for Carousel Engine v2
"""


class CarouselEngineError(Exception):
    """Base exception for Carousel Engine"""
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GENERIC_ERROR"


class NotionAPIError(CarouselEngineError):
    """Notion API related errors"""
    def __init__(self, message: str, page_id: str = None):
        super().__init__(message, "NOTION_API_ERROR")
        self.page_id = page_id


class GoogleDriveError(CarouselEngineError):
    """Google Drive API related errors"""
    def __init__(self, message: str, folder_id: str = None):
        super().__init__(message, "GOOGLE_DRIVE_ERROR")
        self.folder_id = folder_id


class OpenAIError(CarouselEngineError):
    """OpenAI API related errors"""
    def __init__(self, message: str, prompt: str = None):
        super().__init__(message, "OPENAI_ERROR")
        self.prompt = prompt


class ImageProcessingError(CarouselEngineError):
    """Image processing related errors"""
    def __init__(self, message: str, image_path: str = None):
        super().__init__(message, "IMAGE_PROCESSING_ERROR")
        self.image_path = image_path


class ContentProcessingError(CarouselEngineError):
    """Content processing related errors"""
    def __init__(self, message: str, content: str = None):
        super().__init__(message, "CONTENT_PROCESSING_ERROR")
        self.content = content


class CostLimitExceededError(CarouselEngineError):
    """Cost limit exceeded error"""
    def __init__(self, message: str, estimated_cost: float = None, limit: float = None):
        super().__init__(message, "COST_LIMIT_EXCEEDED")
        self.estimated_cost = estimated_cost
        self.limit = limit


class WebhookValidationError(CarouselEngineError):
    """Webhook validation error"""
    def __init__(self, message: str, payload: dict = None):
        super().__init__(message, "WEBHOOK_VALIDATION_ERROR")
        self.payload = payload


class ConfigurationError(CarouselEngineError):
    """Configuration related errors"""
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, "CONFIGURATION_ERROR")
        self.config_key = config_key