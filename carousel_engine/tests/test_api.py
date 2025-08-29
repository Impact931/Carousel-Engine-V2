"""
Tests for the FastAPI application
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from ..api.main import app
from ..core.models import CarouselResponse


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_engine():
    """Mock carousel engine"""
    engine = Mock()
    engine.generate_carousel = AsyncMock()
    engine.notion = Mock()
    engine.notion.get_page = AsyncMock()
    engine.get_processing_metrics = Mock()
    engine.get_all_metrics = Mock()
    engine.health_check = AsyncMock()
    return engine


class TestAPI:
    """Test cases for API endpoints"""

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Carousel Engine v2"
        assert "version" in data

    def test_version_endpoint(self, client):
        """Test version endpoint"""
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "environment" in data

    @patch('carousel_engine.api.main.app.state')
    def test_health_check_endpoint(self, mock_state, client, mock_engine):
        """Test health check endpoint"""
        mock_state.engine = mock_engine
        mock_engine.health_check.return_value = {
            "engine": "healthy",
            "services": {
                "notion": "healthy",
                "google_drive": "healthy",
                "openai": "healthy"
            },
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    @patch('carousel_engine.api.main.app.state')
    def test_generate_carousel_endpoint(self, mock_state, client, mock_engine):
        """Test carousel generation endpoint"""
        mock_state.engine = mock_engine
        mock_engine.generate_carousel.return_value = CarouselResponse(
            success=True,
            notion_page_id="test_page_id",
            slides_generated=3,
            google_drive_folder_url="https://drive.google.com/test",
            processing_time_seconds=5.0,
            estimated_cost=0.05
        )
        
        response = client.post(
            "/api/generate",
            json={"notion_page_id": "test_page_id"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["notion_page_id"] == "test_page_id"
        assert data["slides_generated"] == 3

    @patch('carousel_engine.api.main.app.state')
    def test_generate_carousel_async_endpoint(self, mock_state, client, mock_engine):
        """Test async carousel generation endpoint"""
        mock_state.engine = mock_engine
        
        response = client.post(
            "/api/generate-async",
            json={"notion_page_id": "test_page_id"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["notion_page_id"] == "test_page_id"

    @patch('carousel_engine.api.main.app.state')
    def test_carousel_status_endpoint(self, mock_state, client, mock_engine):
        """Test carousel status endpoint"""
        from ..core.models import NotionPage, CarouselFormat, CarouselStatus
        from datetime import datetime
        
        mock_state.engine = mock_engine
        mock_notion_page = NotionPage(
            id="test_page_id",
            title="Test Page",
            content="Test content",
            format=CarouselFormat.FACEBOOK,
            status=CarouselStatus.COMPLETED,
            google_folder_id=None,
            google_folder_url="https://drive.google.com/test",
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow()
        )
        mock_engine.notion.get_page.return_value = mock_notion_page
        mock_engine.get_processing_metrics.return_value = None
        
        response = client.get("/api/status/test_page_id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["notion_page_id"] == "test_page_id"
        assert data["title"] == "Test Page"
        assert data["status"] == "completed"

    @patch('carousel_engine.api.main.app.state')
    def test_list_carousels_endpoint(self, mock_state, client, mock_engine):
        """Test list carousels endpoint"""
        mock_state.engine = mock_engine
        mock_engine.get_all_metrics.return_value = {}
        
        response = client.get("/api/list")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_processed" in data
        assert "carousels" in data

    def test_webhook_test_endpoint(self, client):
        """Test webhook test endpoint"""
        response = client.get("/webhook/test")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "webhook endpoint operational"

    @patch('carousel_engine.api.main.app.state')
    def test_webhook_notion_endpoint(self, mock_state, client, mock_engine):
        """Test Notion webhook endpoint"""
        mock_state.engine = mock_engine
        
        webhook_payload = {
            "type": "page",
            "data": {
                "id": "test_page_id"
            }
        }
        
        response = client.post("/webhook/notion", json=webhook_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["page_id"] == "test_page_id"

    def test_webhook_notion_invalid_payload(self, client):
        """Test Notion webhook with invalid payload"""
        invalid_payload = {"invalid": "payload"}
        
        response = client.post("/webhook/notion", json=invalid_payload)
        
        assert response.status_code == 400

    def test_webhook_notion_non_page_event(self, client):
        """Test Notion webhook with non-page event"""
        webhook_payload = {
            "type": "database",
            "data": {
                "id": "test_database_id"
            }
        }
        
        response = client.post("/webhook/notion", json=webhook_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    @patch('carousel_engine.api.main.app.state')
    def test_services_health_endpoint(self, mock_state, client, mock_engine):
        """Test services health endpoint"""
        mock_state.engine = mock_engine
        mock_engine.health_check.return_value = {
            "services": {
                "notion": "healthy",
                "google_drive": "healthy",
                "openai": "healthy"
            }
        }
        
        response = client.get("/health/services")
        
        assert response.status_code == 200
        data = response.json()
        assert "notion" in data
        assert "google_drive" in data
        assert "openai" in data

    @patch('carousel_engine.api.main.app.state')
    def test_health_metrics_endpoint(self, mock_state, client, mock_engine):
        """Test health metrics endpoint"""
        from ..core.models import ProcessingMetrics
        from datetime import datetime
        
        mock_state.engine = mock_engine
        mock_metrics = {
            "page1": ProcessingMetrics(
                notion_page_id="page1",
                total_processing_time=5.0,
                notion_fetch_time=1.0,
                content_processing_time=1.0,
                image_generation_time=2.0,
                google_drive_upload_time=1.0,
                notion_update_time=0.5,
                timestamp=datetime.utcnow()
            )
        }
        mock_engine.get_all_metrics.return_value = mock_metrics
        
        response = client.get("/health/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_carousel_runs" in data
        assert data["total_carousel_runs"] == 1