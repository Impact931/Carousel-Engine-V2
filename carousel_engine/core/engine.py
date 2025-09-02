"""
Core Carousel Engine for automated carousel generation
"""

import logging
import time
from datetime import datetime
from typing import List, Tuple, Optional

from ..services.notion import NotionService
from ..services.google_drive import GoogleDriveService
from ..services.openai_service import OpenAIService
from ..utils.image_processor import ImageProcessor
from ..utils.content_processor import ContentProcessor
from ..core.config import config
from ..core.models import (
    CarouselSlide, 
    CarouselResponse, 
    CarouselStatus,
    CostTracking,
    ProcessingMetrics
)
from ..core.exceptions import (
    CarouselEngineError,
    CostLimitExceededError,
    ContentProcessingError
)

logger = logging.getLogger(__name__)


class CarouselEngine:
    """Main engine for automated carousel generation"""
    
    def __init__(
        self,
        notion_service: Optional[NotionService] = None,
        google_drive_service: Optional[GoogleDriveService] = None,
        openai_service: Optional[OpenAIService] = None,
        image_processor: Optional[ImageProcessor] = None,
        content_processor: Optional[ContentProcessor] = None
    ):
        """Initialize Carousel Engine with conditional service initialization
        
        Args:
            notion_service: Notion API service instance
            google_drive_service: Google Drive API service instance
            openai_service: OpenAI API service instance
            image_processor: Image processing utility instance
            content_processor: Content processing utility instance
        """
        # Initialize services with error handling for serverless environments
        self.notion = None
        self.google_drive = None
        self.openai = None
        self.image_processor = None
        self.content_processor = None
        
        try:
            self.notion = notion_service or NotionService()
        except Exception as e:
            logger.warning(f"Failed to initialize Notion service: {e}")
        
        try:
            self.google_drive = google_drive_service or GoogleDriveService()
        except Exception as e:
            logger.warning(f"Failed to initialize Google Drive service: {e}")
        
        try:
            self.openai = openai_service or OpenAIService()
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI service: {e}")
        
        try:
            self.image_processor = image_processor or ImageProcessor()
        except Exception as e:
            logger.warning(f"Failed to initialize Image Processor: {e}")
        
        try:
            self.content_processor = content_processor or ContentProcessor()
        except Exception as e:
            logger.warning(f"Failed to initialize Content Processor: {e}")
        
        # Performance tracking
        self.metrics = {}
    
    async def generate_carousel(
        self, 
        notion_page_id: str,
        force_regenerate: bool = False
    ) -> CarouselResponse:
        """Generate a complete carousel from Notion page
        
        Args:
            notion_page_id: Notion page ID to process
            force_regenerate: Force regeneration even if already processed
            
        Returns:
            CarouselResponse with generation results
            
        Raises:
            CarouselEngineError: If carousel generation fails
        """
        start_time = time.time()
        self.openai.reset_cost_tracking()
        
        try:
            logger.info(f"Starting carousel generation for page: {notion_page_id}")
            
            # Step 1: Fetch content from Notion
            fetch_start = time.time()
            notion_page = await self.notion.get_page(notion_page_id)
            fetch_time = time.time() - fetch_start
            
            logger.info(f"Retrieved Notion page: {notion_page.title}")
            
            # Step 1.5: Retrieve client system message if available
            client_system_message = await self._get_client_system_message(notion_page)
            if client_system_message:
                logger.info("Found client system message - will use for personalized content generation")
            else:
                logger.info("No client system message found - using default content generation")
            
            # Check if already processed (unless force regenerate)
            if not force_regenerate and notion_page.format.value.lower() == "complete":
                logger.info(f"Page already processed with format: {notion_page.format.value}")
                return CarouselResponse(
                    success=True,
                    notion_page_id=notion_page_id,
                    slides_generated=0,
                    google_drive_folder_url=notion_page.google_folder_url,
                    processing_time_seconds=0,
                    estimated_cost=0,
                    error_message="Already processed (use force_regenerate=True to regenerate)"
                )
            
            # Update status to processing
            await self.notion.update_page_status(notion_page_id, CarouselStatus.PROCESSING)
            
            # Step 2: Process and optimize content
            content_start = time.time()
            optimized_slides = await self._process_content(notion_page, client_system_message)
            content_time = time.time() - content_start
            
            # Step 3: Generate actual background image using DALL-E 3
            image_gen_start = time.time()
            background_image_data, image_cost = await self.openai.generate_background_image(
                notion_page.title,
                "professional",  # theme
                client_system_message or "",  # client context for theming
                "1024x1024"  # size
            )
            image_gen_time = time.time() - image_gen_start
            
            # Step 4: Create carousel slides with real background image
            slide_images = await self._create_slide_images(optimized_slides, background_image_data)
            
            # Step 5: Upload to Google Drive
            upload_start = time.time()
            folder_url = await self._upload_to_google_drive(
                slide_images, 
                notion_page,
                notion_page.google_folder_id
            )
            upload_time = time.time() - upload_start
            
            # Step 6: Update Notion with results
            update_start = time.time()
            await self.notion.update_page_status(
                notion_page_id, 
                CarouselStatus.REVIEW,
                folder_url,
                system_message_used=bool(client_system_message),
                mark_format_complete=True
            )
            update_time = time.time() - update_start
            
            # Calculate metrics
            total_time = time.time() - start_time
            total_cost = self.openai.get_total_cost()
            
            # Store metrics
            self.metrics[notion_page_id] = ProcessingMetrics(
                notion_page_id=notion_page_id,
                total_processing_time=total_time,
                notion_fetch_time=fetch_time,
                content_processing_time=content_time,
                image_generation_time=image_gen_time,
                google_drive_upload_time=upload_time,
                notion_update_time=update_time
            )
            
            # Store cost tracking
            cost_tracking = CostTracking(
                notion_page_id=notion_page_id,
                openai_cost=total_cost,
                google_drive_cost=0.0,  # Generally free for reasonable usage
                notion_cost=0.0,  # Generally free for reasonable usage
                total_cost=total_cost
            )
            
            logger.info(
                f"Carousel generation completed successfully. "
                f"Time: {total_time:.2f}s, Cost: ${total_cost:.4f}, "
                f"Slides: {len(slide_images)}"
            )
            
            return CarouselResponse(
                success=True,
                notion_page_id=notion_page_id,
                slides_generated=len(slide_images),
                google_drive_folder_url=folder_url,
                processing_time_seconds=total_time,
                estimated_cost=total_cost
            )
            
        except CostLimitExceededError as e:
            logger.error(f"Cost limit exceeded: {e}")
            await self.notion.update_page_status(notion_page_id, CarouselStatus.ERROR)
            
            return CarouselResponse(
                success=False,
                notion_page_id=notion_page_id,
                slides_generated=0,
                processing_time_seconds=time.time() - start_time,
                estimated_cost=self.openai.get_total_cost(),
                error_message=str(e)
            )
            
        except Exception as e:
            logger.error(f"Carousel generation failed: {e}")
            await self.notion.update_page_status(notion_page_id, CarouselStatus.ERROR)
            
            return CarouselResponse(
                success=False,
                notion_page_id=notion_page_id,
                slides_generated=0,
                processing_time_seconds=time.time() - start_time,
                estimated_cost=self.openai.get_total_cost(),
                error_message=str(e)
            )
    
    async def _process_content(self, notion_page, client_system_message: Optional[str] = None) -> List[CarouselSlide]:
        """Process and optimize content for carousel slides
        
        Args:
            notion_page: NotionPage object
            client_system_message: Optional client-specific system message for personalization
            
        Returns:
            List of processed CarouselSlide objects
        """
        try:
            # Try AI optimization first
            try:
                optimized_content, _ = await self.openai.optimize_content_for_slides(
                    notion_page.content,
                    max_slides=config.max_carousel_slides,
                    lines_per_slide=config.lines_per_slide,
                    client_system_message=client_system_message
                )
                logger.info("Successfully optimized content with AI")
            except Exception as e:
                logger.warning(f"AI content optimization failed, using fallback: {e}")
                optimized_content = None
            
            # Process into slides
            slides = self.content_processor.process_content_to_slides(
                notion_page.title,
                notion_page.content,
                optimized_content
            )
            
            # Validate slides
            for slide in slides:
                is_valid, error_msg = self.content_processor.validate_slide_content(slide)
                if not is_valid:
                    raise ContentProcessingError(f"Invalid slide {slide.slide_number}: {error_msg}")
            
            logger.info(f"Successfully processed {len(slides)} slides")
            return slides
            
        except Exception as e:
            raise ContentProcessingError(f"Failed to process content: {e}")
    
    async def _create_slide_images(
        self, 
        slides: List[CarouselSlide], 
        background_image_data: bytes
    ) -> List[Tuple[bytes, str]]:
        """Create image data for all slides using real background image
        
        Args:
            slides: List of CarouselSlide objects
            background_image_data: Real background image data from DALL-E 3
            
        Returns:
            List of (image_data, filename) tuples
        """
        slide_images = []
        
        for slide in slides:
            try:
                # Generate filename (content slides only)
                filename = f"{slide.slide_number:02d}_slide.png"
                
                # Use the real generated background image directly
                # This is now a professional DALL-E 3 generated real estate image
                
                # Create slide image with professional background and proper text overlay
                image_data = self.image_processor.create_carousel_slide(
                    background_image_data,
                    slide.content,
                    is_title_slide=False,
                    slide_number=slide.slide_number
                )
                
                slide_images.append((image_data, filename))
                logger.debug(f"Created image for slide {slide.slide_number}")
                
            except Exception as e:
                raise CarouselEngineError(f"Failed to create image for slide {slide.slide_number}: {e}")
        
        logger.info(f"Successfully created {len(slide_images)} slide images")
        return slide_images
    
    def _create_simple_background(self, description: str) -> bytes:
        """Create a simple background image based on GPT description
        
        Args:
            description: GPT-generated background description
            
        Returns:
            Simple background image as bytes
        """
        try:
            from PIL import Image, ImageDraw
            from io import BytesIO
            
            # Create a simple gradient or solid color background
            # Parse description for color hints
            description_lower = description.lower()
            
            # Default professional colors
            if any(word in description_lower for word in ['warm', 'cozy', 'inviting']):
                color = (250, 245, 235)  # Warm off-white
            elif any(word in description_lower for word in ['luxury', 'premium', 'sophisticated']):
                color = (248, 248, 245)  # Elegant cream
            elif any(word in description_lower for word in ['vibrant', 'bright', 'energetic']):
                color = (245, 250, 255)  # Light blue tint
            elif any(word in description_lower for word in ['modern', 'clean', 'minimalist']):
                color = (250, 250, 250)  # Clean white
            else:
                color = (248, 248, 248)  # Professional light gray
            
            # Create image with appropriate size
            width, height = 1080, 1080  # Standard social media size
            image = Image.new('RGB', (width, height), color)
            
            # Add subtle texture/gradient
            draw = ImageDraw.Draw(image)
            for i in range(height):
                alpha = int(255 * (1 - i / height * 0.1))  # Subtle gradient
                gradient_color = tuple(min(255, c + alpha // 20) for c in color)
                draw.line([(0, i), (width, i)], fill=gradient_color)
            
            # Convert to bytes
            buffer = BytesIO()
            image.save(buffer, format='PNG', quality=95)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to create simple background: {e}")
            # Return a basic white background as fallback
            from PIL import Image
            from io import BytesIO
            
            image = Image.new('RGB', (1080, 1080), (255, 255, 255))
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            return buffer.getvalue()
    
    async def _upload_to_google_drive(
        self, 
        slide_images: List[Tuple[bytes, str]], 
        notion_page,
        parent_folder_id: Optional[str] = None
    ) -> str:
        """Upload slide images to Google Drive
        
        Args:
            slide_images: List of (image_data, filename) tuples
            notion_page: NotionPage object
            parent_folder_id: Parent folder ID for upload
            
        Returns:
            Google Drive folder URL
        """
        try:
            # Create folder name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"{notion_page.title}_{timestamp}"
            
            # Clean folder name (remove invalid characters)
            folder_name = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_')).strip()
            folder_name = folder_name[:100]  # Limit length
            
            # Create folder
            folder_id, folder_url = await self.google_drive.create_folder(
                folder_name,
                parent_folder_id
            )
            
            logger.info(f"Created Google Drive folder: {folder_name}")
            
            # Upload all images
            uploaded_files = await self.google_drive.upload_multiple_images(
                slide_images,
                folder_id
            )
            
            logger.info(f"Uploaded {len(uploaded_files)} images to Google Drive")
            return folder_url
            
        except Exception as e:
            raise CarouselEngineError(f"Failed to upload to Google Drive: {e}")
    
    def get_processing_metrics(self, notion_page_id: str) -> Optional[ProcessingMetrics]:
        """Get processing metrics for a specific page
        
        Args:
            notion_page_id: Notion page ID
            
        Returns:
            ProcessingMetrics object or None if not found
        """
        return self.metrics.get(notion_page_id)
    
    def get_all_metrics(self) -> dict:
        """Get all processing metrics
        
        Returns:
            Dictionary of all metrics
        """
        return self.metrics.copy()
    
    async def _get_client_system_message(self, notion_page) -> Optional[str]:
        """Retrieve client system message if available
        
        Args:
            notion_page: NotionPage object
            
        Returns:
            Client system message content or None if not found
        """
        try:
            logger.info("Searching for client system message using Project field...")
            
            # Extract the 'Project' field value from the carousel page
            page_properties = notion_page.properties
            project_field = page_properties.get("Project", {})
            
            # Handle different Project field types (relation, select, rich_text, etc.)
            project_name = None
            
            if project_field.get("type") == "relation":
                # If Project is a relation field, we need to get the related page
                relation_pages = project_field.get("relation", [])
                if relation_pages:
                    # Get the first related page ID and fetch its name
                    related_page_id = relation_pages[0].get("id")
                    if related_page_id:
                        try:
                            related_page = self.notion.client.pages.retrieve(page_id=related_page_id)
                            project_name = self.notion._extract_title(related_page)
                            logger.info(f"Found Project relation: {project_name}")
                        except Exception as e:
                            logger.warning(f"Error fetching related project page: {e}")
            
            elif project_field.get("type") == "select":
                # If Project is a select field
                select_option = project_field.get("select")
                if select_option:
                    project_name = select_option.get("name")
                    logger.info(f"Found Project select: {project_name}")
            
            elif project_field.get("type") == "rich_text":
                # If Project is a rich text field
                rich_text = project_field.get("rich_text", [])
                if rich_text:
                    project_name = "".join([part.get("plain_text", "") for part in rich_text])
                    logger.info(f"Found Project rich_text: {project_name}")
            
            elif project_field.get("type") == "title":
                # If Project is a title field
                title = project_field.get("title", [])
                if title:
                    project_name = "".join([part.get("plain_text", "") for part in title])
                    logger.info(f"Found Project title: {project_name}")
            
            if not project_name:
                logger.warning("No Project field value found in carousel page")
                return None
            
            # Now search for matching client project in Client Project Database
            # Match Project field value with Client_Project_Name field
            logger.info(f"Searching Client Project Database for Client_Project_Name matching: {project_name}")
            
            try:
                # Query client project database for Client_Project_Name matching the project name
                matching_projects = await self.notion.query_client_projects(
                    config.client_project_database_id,
                    project_name
                )
                
                if matching_projects:
                    project = matching_projects[0]  # Use first match
                    properties = project.get("properties", {})
                    
                    logger.info(f"Found matching client project in database")
                    
                    # Check if system message URL exists
                    system_message_url_prop = properties.get("System_Message_URL", {})
                    system_message_url = system_message_url_prop.get("url")
                    
                    system_message_generated = properties.get("System_Message_Generated", {}).get("checkbox", False)
                    
                    if system_message_url and system_message_generated:
                        logger.info(f"Found client project with system message for: {project_name}")
                        
                        # Extract Google Drive file ID from URL
                        if "drive.google.com" in system_message_url and "/file/d/" in system_message_url:
                            # Extract file ID from Google Drive URL
                            file_id = system_message_url.split("/file/d/")[1].split("/")[0]
                            
                            # Download system message content from Google Drive
                            system_message_content = await self.google_drive.download_text_file(file_id)
                            
                            logger.info(f"Successfully retrieved system message ({len(system_message_content)} chars)")
                            
                            # Track usage in Client Project Database
                            try:
                                await self.notion.update_client_project_usage_tracking(
                                    project.get("id"),
                                    notion_page.id,
                                    notion_page.title
                                )
                                logger.info("Updated Client Project Database usage tracking")
                            except Exception as e:
                                logger.warning(f"Failed to update Client Project usage tracking: {e}")
                            
                            return system_message_content
                        else:
                            logger.warning(f"System message URL format not recognized: {system_message_url}")
                    else:
                        logger.info(f"Project found but no system message available: generated={system_message_generated}, url={bool(system_message_url)}")
                else:
                    logger.info(f"No matching client project found for: {project_name}")
                
            except Exception as e:
                logger.warning(f"Error searching for client project '{project_name}': {e}")
            
            logger.info("No matching client project with system message found")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving client system message: {e}")
            return None
    
    async def health_check(self) -> dict:
        """Perform health check on all services
        
        Returns:
            Health check results
        """
        health_status = {
            "engine": "healthy",
            "services": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Test Notion API
        try:
            # Try to list database (basic connectivity test)
            test_response = self.notion.client.databases.query(
                database_id=config.notion_database_id,
                page_size=1
            )
            health_status["services"]["notion"] = "healthy"
        except Exception as e:
            health_status["services"]["notion"] = f"unhealthy: {e}"
        
        # Test Google Drive API
        try:
            # Try to get drive info (basic connectivity test)
            about = self.google_drive.service.about().get(fields="user").execute()
            health_status["services"]["google_drive"] = "healthy"
        except Exception as e:
            health_status["services"]["google_drive"] = f"unhealthy: {e}"
        
        # Test OpenAI API
        try:
            # Try to list models (basic connectivity test)
            models = self.openai.client.models.list()
            health_status["services"]["openai"] = "healthy"
        except Exception as e:
            health_status["services"]["openai"] = f"unhealthy: {e}"
        
        # Overall health
        unhealthy_services = [k for k, v in health_status["services"].items() if "unhealthy" in str(v)]
        if unhealthy_services:
            health_status["engine"] = f"degraded: {', '.join(unhealthy_services)} unhealthy"
        
        return health_status