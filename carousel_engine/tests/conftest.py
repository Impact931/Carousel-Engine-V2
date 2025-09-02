"""
Pytest configuration and fixtures
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Generator, Any

from ..core.config import Config
from ..core.engine import CarouselEngine
from ..services.notion import NotionService
from ..services.google_drive import GoogleDriveService
from ..services.openai_service import OpenAIService
from ..utils.image_processor import ImageProcessor
from ..utils.content_processor import ContentProcessor


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, Any, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Test configuration"""
    return Config(
        notion_api_key="test_notion_key",
        google_credentials_json='{"type": "service_account", "project_id": "test"}',
        openai_api_key="test_openai_key",
        notion_database_id="test_database_id",
        environment="test",
        debug=True
    )


@pytest.fixture
def mock_notion_service():
    """Mock Notion service"""
    mock = Mock(spec=NotionService)
    mock.get_page = AsyncMock()
    mock.update_page_status = AsyncMock()
    return mock


@pytest.fixture
def mock_google_drive_service():
    """Mock Google Drive service"""
    mock = Mock(spec=GoogleDriveService)
    mock.create_folder = AsyncMock()
    mock.upload_image = AsyncMock()
    mock.upload_multiple_images = AsyncMock()
    mock.get_folder_info = AsyncMock()
    return mock


@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service"""
    mock = Mock(spec=OpenAIService)
    mock.generate_background_description = AsyncMock()
    mock.optimize_content_for_slides = AsyncMock()
    mock.get_total_cost = Mock(return_value=0.0)
    mock.reset_cost_tracking = Mock()
    return mock


@pytest.fixture
def mock_image_processor():
    """Mock image processor"""
    mock = Mock(spec=ImageProcessor)
    mock.create_carousel_slide = Mock(return_value=b"fake_image_data")
    return mock


@pytest.fixture
def mock_content_processor():
    """Mock content processor"""
    mock = Mock(spec=ContentProcessor)
    mock.process_content_to_slides = Mock()
    mock.validate_slide_content = Mock(return_value=(True, ""))
    return mock


@pytest.fixture
def carousel_engine(
    mock_notion_service,
    mock_google_drive_service,
    mock_openai_service,
    mock_image_processor,
    mock_content_processor
):
    """Carousel engine with mocked dependencies"""
    return CarouselEngine(
        notion_service=mock_notion_service,
        google_drive_service=mock_google_drive_service,
        openai_service=mock_openai_service,
        image_processor=mock_image_processor,
        content_processor=mock_content_processor
    )


@pytest.fixture
def sample_notion_page():
    """Sample Notion page data"""
    from ..core.models import NotionPage, CarouselFormat, CarouselStatus
    from datetime import datetime
    
    return NotionPage(
        id="test_page_id",
        title="Test Carousel Title",
        content="This is test content for the carousel.\n\nIt has multiple paragraphs.\n\nAnd should be processed correctly.",
        format=CarouselFormat.FACEBOOK,
        status=CarouselStatus.READY,
        google_folder_id=None,
        google_folder_url=None,
        created_time=datetime.utcnow(),
        last_edited_time=datetime.utcnow()
    )


@pytest.fixture
def sample_carousel_slides():
    """Sample carousel slides"""
    from ..core.models import CarouselSlide
    
    return [
        CarouselSlide(
            slide_number=0,
            title="Test Carousel Title",
            content="Test Carousel Title",
            is_title_slide=True
        ),
        CarouselSlide(
            slide_number=1,
            content="This is test content for the carousel."
        ),
        CarouselSlide(
            slide_number=2,
            content="It has multiple paragraphs."
        )
    ]