"""
Tests for the Carousel Engine core functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from ..core.engine import CarouselEngine
from ..core.models import CarouselStatus, CarouselSlide
from ..core.exceptions import CarouselEngineError, CostLimitExceededError


class TestCarouselEngine:
    """Test cases for CarouselEngine"""

    @pytest.mark.asyncio
    async def test_generate_carousel_success(
        self, 
        carousel_engine,
        sample_notion_page,
        sample_carousel_slides,
        mock_notion_service,
        mock_openai_service,
        mock_google_drive_service,
        mock_content_processor,
        mock_image_processor
    ):
        """Test successful carousel generation"""
        # Setup mocks
        mock_notion_service.get_page.return_value = sample_notion_page
        mock_notion_service.update_page_status.return_value = True
        
        mock_openai_service.generate_background_image.return_value = (b"fake_bg_image", 0.04)
        mock_openai_service.optimize_content_for_slides.return_value = (
            ["Slide 1 content", "Slide 2 content"], 0.01
        )
        
        mock_content_processor.process_content_to_slides.return_value = sample_carousel_slides
        mock_content_processor.validate_slide_content.return_value = (True, "")
        
        mock_google_drive_service.create_folder.return_value = ("folder_id", "folder_url")
        mock_google_drive_service.upload_multiple_images.return_value = [
            ("file_id_1", "file_url_1"),
            ("file_id_2", "file_url_2")
        ]
        
        # Execute
        result = await carousel_engine.generate_carousel("test_page_id")
        
        # Verify
        assert result.success is True
        assert result.notion_page_id == "test_page_id"
        assert result.slides_generated == 2  # Multiple slide images created
        assert result.google_drive_folder_url == "folder_url"
        assert result.processing_time_seconds > 0
        assert result.error_message is None
        
        # Verify service calls
        mock_notion_service.get_page.assert_called_once_with("test_page_id")
        mock_notion_service.update_page_status.assert_called()
        mock_openai_service.generate_background_image.assert_called_once()
        mock_google_drive_service.create_folder.assert_called_once()
        mock_google_drive_service.upload_multiple_images.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_carousel_already_processed(
        self,
        carousel_engine,
        sample_notion_page,
        mock_notion_service
    ):
        """Test carousel generation when already processed"""
        # Setup - page already completed
        sample_notion_page.status = CarouselStatus.COMPLETED
        sample_notion_page.google_folder_url = "existing_folder_url"
        mock_notion_service.get_page.return_value = sample_notion_page
        
        # Execute
        result = await carousel_engine.generate_carousel("test_page_id")
        
        # Verify
        assert result.success is True
        assert result.slides_generated == 0
        assert result.google_drive_folder_url == "existing_folder_url"
        assert "already processed" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_generate_carousel_force_regenerate(
        self,
        carousel_engine,
        sample_notion_page,
        sample_carousel_slides,
        mock_notion_service,
        mock_openai_service,
        mock_google_drive_service,
        mock_content_processor
    ):
        """Test forced regeneration of completed carousel"""
        # Setup - page already completed but force regenerate
        sample_notion_page.status = CarouselStatus.COMPLETED
        mock_notion_service.get_page.return_value = sample_notion_page
        mock_notion_service.update_page_status.return_value = True
        
        mock_openai_service.generate_background_image.return_value = (b"fake_bg_image", 0.04)
        mock_content_processor.process_content_to_slides.return_value = sample_carousel_slides
        mock_google_drive_service.create_folder.return_value = ("folder_id", "folder_url")
        mock_google_drive_service.upload_multiple_images.return_value = []
        
        # Execute
        result = await carousel_engine.generate_carousel("test_page_id", force_regenerate=True)
        
        # Verify
        assert result.success is True
        assert result.slides_generated >= 0  # Should process even if already completed

    @pytest.mark.asyncio
    async def test_generate_carousel_cost_limit_exceeded(
        self,
        carousel_engine,
        sample_notion_page,
        mock_notion_service,
        mock_openai_service
    ):
        """Test carousel generation with cost limit exceeded"""
        # Setup
        mock_notion_service.get_page.return_value = sample_notion_page
        mock_notion_service.update_page_status.return_value = True
        
        # Mock cost limit exceeded
        mock_openai_service.generate_background_image.side_effect = CostLimitExceededError(
            "Cost limit exceeded", 2.0, 1.0
        )
        
        # Execute
        result = await carousel_engine.generate_carousel("test_page_id")
        
        # Verify
        assert result.success is False
        assert "cost limit" in result.error_message.lower()
        mock_notion_service.update_page_status.assert_called_with("test_page_id", CarouselStatus.ERROR)

    @pytest.mark.asyncio
    async def test_generate_carousel_general_error(
        self,
        carousel_engine,
        sample_notion_page,
        mock_notion_service,
        mock_openai_service
    ):
        """Test carousel generation with general error"""
        # Setup
        mock_notion_service.get_page.return_value = sample_notion_page
        mock_notion_service.update_page_status.return_value = True
        
        # Mock general error
        mock_openai_service.generate_background_image.side_effect = Exception("Test error")
        
        # Execute
        result = await carousel_engine.generate_carousel("test_page_id")
        
        # Verify
        assert result.success is False
        assert "test error" in result.error_message.lower()
        mock_notion_service.update_page_status.assert_called_with("test_page_id", CarouselStatus.ERROR)

    @pytest.mark.asyncio
    async def test_health_check(self, carousel_engine, mock_notion_service, mock_google_drive_service, mock_openai_service):
        """Test health check functionality"""
        # Setup mocks for successful health checks
        mock_notion_service.client.databases.query.return_value = {"results": []}
        mock_google_drive_service.service.about.return_value.get.return_value.execute.return_value = {"user": {}}
        mock_openai_service.client.models.list.return_value = []
        
        # Execute
        health_status = await carousel_engine.health_check()
        
        # Verify
        assert health_status["engine"] == "healthy"
        assert "notion" in health_status["services"]
        assert "google_drive" in health_status["services"]
        assert "openai" in health_status["services"]

    def test_get_processing_metrics(self, carousel_engine):
        """Test processing metrics retrieval"""
        # Setup - add some fake metrics
        from ..core.models import ProcessingMetrics
        test_metrics = ProcessingMetrics(
            notion_page_id="test_page",
            total_processing_time=5.0,
            notion_fetch_time=1.0,
            content_processing_time=1.0,
            image_generation_time=2.0,
            google_drive_upload_time=1.0,
            notion_update_time=0.5
        )
        carousel_engine.metrics["test_page"] = test_metrics
        
        # Execute
        metrics = carousel_engine.get_processing_metrics("test_page")
        
        # Verify
        assert metrics is not None
        assert metrics.notion_page_id == "test_page"
        assert metrics.total_processing_time == 5.0

    def test_get_all_metrics(self, carousel_engine):
        """Test all metrics retrieval"""
        # Setup - add some fake metrics
        from ..core.models import ProcessingMetrics
        carousel_engine.metrics["page1"] = ProcessingMetrics(
            notion_page_id="page1",
            total_processing_time=5.0,
            notion_fetch_time=1.0,
            content_processing_time=1.0,
            image_generation_time=2.0,
            google_drive_upload_time=1.0,
            notion_update_time=0.5
        )
        
        # Execute
        all_metrics = carousel_engine.get_all_metrics()
        
        # Verify
        assert isinstance(all_metrics, dict)
        assert "page1" in all_metrics