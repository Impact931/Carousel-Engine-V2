"""
Notion API service for Carousel Engine v2
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from notion_client import Client
from notion_client.errors import APIResponseError

from ..core.config import config
from ..core.models import NotionPage, CarouselFormat, CarouselStatus
from ..core.exceptions import NotionAPIError

logger = logging.getLogger(__name__)


class NotionService:
    """Service for interacting with Notion API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Notion service
        
        Args:
            api_key: Notion API key, defaults to config value
        """
        self.client = Client(auth=api_key or config.notion_api_key)
        self.database_id = config.notion_database_id
        
    async def get_page(self, page_id: str) -> NotionPage:
        """Retrieve a Notion page by ID
        
        Args:
            page_id: The Notion page ID
            
        Returns:
            NotionPage model with page data
            
        Raises:
            NotionAPIError: If page retrieval fails
        """
        try:
            logger.info(f"Fetching Notion page: {page_id}")
            
            # Get page content
            page = self.client.pages.retrieve(page_id=page_id)
            
            # Get page content blocks
            blocks = self.client.blocks.children.list(block_id=page_id)
            
            # Extract title
            title = self._extract_title(page)
            
            # Extract content text from blocks
            content = self._extract_content(blocks)
            
            # If no content in blocks, use title as content (common for structured entries)
            if not content.strip() and title:
                content = title
                logger.info(f"No block content found, using title as content: {len(content)} chars")
            
            # Extract properties
            properties = page.get("properties", {})
            
            # Parse format and status
            format_prop = self._get_property_value(properties, "Format", CarouselFormat.FACEBOOK.value)
            status_prop = self._get_property_value(properties, "Status", CarouselStatus.DRAFT.value)
            
            # Parse Google Drive folder ID
            google_folder_id = self._get_property_value(properties, "Google Folder ID")
            google_folder_url = self._get_property_value(properties, "Google Folder URL")
            
            # Parse timestamps
            created_time = datetime.fromisoformat(page["created_time"].replace("Z", "+00:00"))
            last_edited_time = datetime.fromisoformat(page["last_edited_time"].replace("Z", "+00:00"))
            
            return NotionPage(
                id=page_id,
                title=title,
                content=content,
                format=CarouselFormat(format_prop.lower()),
                status=CarouselStatus(status_prop.lower()),
                google_folder_id=google_folder_id,
                google_folder_url=google_folder_url,
                created_time=created_time,
                last_edited_time=last_edited_time,
                properties=properties
            )
            
        except APIResponseError as e:
            error_msg = f"Failed to retrieve Notion page {page_id}: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg, page_id=page_id)
        except Exception as e:
            error_msg = f"Unexpected error retrieving Notion page {page_id}: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg, page_id=page_id)
    
    async def update_page_status(
        self, 
        page_id: str, 
        status: CarouselStatus,
        google_folder_url: Optional[str] = None,
        system_message_used: bool = False,
        mark_format_complete: bool = False
    ) -> bool:
        """Update a Notion page's status, Format, Google Drive URL, and system message usage tracking
        
        Args:
            page_id: The Notion page ID
            status: New status to set
            google_folder_url: Google Drive folder URL to add
            system_message_used: Whether a client system message was used for generation
            mark_format_complete: Whether to change Format from "Carousel" to "Complete"
            
        Returns:
            True if update was successful
            
        Raises:
            NotionAPIError: If page update fails
        """
        try:
            logger.info(f"Updating Notion page {page_id} to status: {status.value}")
            
            # Prepare properties update
            properties = {
                "Status": {
                    "select": {
                        "name": status.value.title()
                    }
                }
            }
            
            # Add Google Drive URL to Images field if provided
            if google_folder_url:
                properties["Images"] = {
                    "url": google_folder_url
                }
                logger.info(f"Adding Google Drive URL to page: {google_folder_url}")
            
            # Update Format field from "Carousel" to "Complete" if requested
            if mark_format_complete:
                properties["Format"] = {
                    "select": {
                        "name": "Complete"
                    }
                }
                logger.info("Updating Format from 'Carousel' to 'Complete'")
            
            # Add system message usage tracking if used
            if system_message_used:
                from datetime import datetime
                
                # Get current page to check available properties
                page = self.client.pages.retrieve(page_id=page_id)
                available_properties = page.get("properties", {})
                
                # Add system message usage fields if they exist
                if "System_Message_Used" in available_properties:
                    properties["System_Message_Used"] = {
                        "checkbox": True
                    }
                    logger.info("Marking System_Message_Used as True")
                
                if "Last_System_Message_Date" in available_properties:
                    properties["Last_System_Message_Date"] = {
                        "date": {
                            "start": datetime.now().isoformat()
                        }
                    }
                    logger.info("Updating Last_System_Message_Date")
            
            # Update the page
            self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            logger.info(f"Successfully updated Notion page {page_id}")
            return True
            
        except APIResponseError as e:
            error_msg = f"Failed to update Notion page {page_id}: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg, page_id=page_id)
        except Exception as e:
            error_msg = f"Unexpected error updating Notion page {page_id}: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg, page_id=page_id)
    
    def _extract_title(self, page: Dict[str, Any]) -> str:
        """Extract title from Notion page
        
        Args:
            page: Notion page object
            
        Returns:
            Page title string
        """
        try:
            properties = page.get("properties", {})
            
            # Look for title property
            for key, prop in properties.items():
                if prop.get("type") == "title":
                    title_parts = prop.get("title", [])
                    if title_parts:
                        return "".join([part.get("plain_text", "") for part in title_parts])
            
            # Fallback to page object title
            if "title" in page:
                return page["title"]
                
            return "Untitled"
            
        except Exception as e:
            logger.warning(f"Error extracting title: {e}")
            return "Untitled"
    
    def _extract_content(self, blocks: Dict[str, Any]) -> str:
        """Extract text content from Notion blocks
        
        Args:
            blocks: Notion blocks response
            
        Returns:
            Combined text content
        """
        content_parts = []
        
        try:
            for block in blocks.get("results", []):
                block_type = block.get("type")
                
                if block_type == "paragraph":
                    text = self._extract_rich_text(block["paragraph"].get("rich_text", []))
                    if text.strip():
                        content_parts.append(text)
                        
                elif block_type == "bulleted_list_item":
                    text = self._extract_rich_text(block["bulleted_list_item"].get("rich_text", []))
                    if text.strip():
                        content_parts.append(f"• {text}")
                        
                elif block_type == "numbered_list_item":
                    text = self._extract_rich_text(block["numbered_list_item"].get("rich_text", []))
                    if text.strip():
                        content_parts.append(f"1. {text}")
                        
                elif block_type == "heading_1":
                    text = self._extract_rich_text(block["heading_1"].get("rich_text", []))
                    if text.strip():
                        content_parts.append(f"# {text}")
                        
                elif block_type == "heading_2":
                    text = self._extract_rich_text(block["heading_2"].get("rich_text", []))
                    if text.strip():
                        content_parts.append(f"## {text}")
                        
                elif block_type == "heading_3":
                    text = self._extract_rich_text(block["heading_3"].get("rich_text", []))
                    if text.strip():
                        content_parts.append(f"### {text}")
            
            return "\n\n".join(content_parts)
            
        except Exception as e:
            logger.error(f"Error extracting content from blocks: {e}")
            return ""
    
    def _extract_rich_text(self, rich_text: list) -> str:
        """Extract plain text from Notion rich text objects
        
        Args:
            rich_text: List of rich text objects
            
        Returns:
            Plain text string
        """
        try:
            return "".join([item.get("plain_text", "") for item in rich_text])
        except Exception as e:
            logger.error(f"Error extracting rich text: {e}")
            return ""
    
    def _get_property_value(self, properties: Dict[str, Any], property_name: str, default: Any = None) -> Any:
        """Get value from Notion property
        
        Args:
            properties: Page properties dict
            property_name: Name of property to extract
            default: Default value if property not found
            
        Returns:
            Property value or default
        """
        try:
            prop = properties.get(property_name, {})
            prop_type = prop.get("type")
            
            if prop_type == "select" and prop.get("select"):
                return prop["select"].get("name")
            elif prop_type == "rich_text":
                return self._extract_rich_text(prop.get("rich_text", []))
            elif prop_type == "title":
                return self._extract_rich_text(prop.get("title", []))
            elif prop_type == "url":
                return prop.get("url")
            elif prop_type == "number":
                return prop.get("number")
            elif prop_type == "checkbox":
                return prop.get("checkbox")
                
            return default
            
        except Exception as e:
            logger.error(f"Error extracting property {property_name}: {e}")
            return default
    
    async def query_database(self, database_id: str, limit: int = 10, format_filter: str = None) -> list:
        """Query a Notion database for pages
        
        Args:
            database_id: The Notion database ID
            limit: Maximum number of pages to return
            format_filter: Filter by Format property value
            
        Returns:
            List of page objects
            
        Raises:
            NotionAPIError: If database query fails
        """
        try:
            logger.info(f"Querying Notion database: {database_id}")
            
            # Build query with optional filter
            query_params = {
                "database_id": database_id,
                "page_size": limit,
                "sorts": [
                    {
                        "property": "Created time",
                        "direction": "descending"
                    }
                ]
            }
            
            # Add format filter if specified
            if format_filter:
                query_params["filter"] = {
                    "property": "Format",
                    "select": {
                        "equals": format_filter
                    }
                }
                logger.info(f"Filtering for Format = {format_filter}")
            
            response = self.client.databases.query(**query_params)
            
            pages = response.get("results", [])
            logger.info(f"Retrieved {len(pages)} pages from database")
            
            return pages
            
        except APIResponseError as e:
            error_msg = f"Notion database query failed: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg)
        except Exception as e:
            error_msg = f"Failed to query Notion database: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg)
    
    async def query_brainstorming_carousels(self, database_id: str, limit: int = 10) -> list:
        """Query for Carousel records with Brainstorming status
        
        Args:
            database_id: The Notion database ID
            limit: Maximum number of pages to return
            
        Returns:
            List of page objects matching Format=Carousel AND Status=Brainstorming
            
        Raises:
            NotionAPIError: If database query fails
        """
        try:
            logger.info(f"Querying database for Carousel records with Brainstorming status")
            
            # Build compound filter for Format='Carousel' AND Status='Brainstorming'
            query_params = {
                "database_id": database_id,
                "page_size": limit,
                "filter": {
                    "and": [
                        {
                            "property": "Format",
                            "select": {
                                "equals": "Carousel"
                            }
                        },
                        {
                            "property": "Status",
                            "select": {
                                "equals": "Brainstorming"
                            }
                        }
                    ]
                },
                "sorts": [
                    {
                        "property": "Created time",
                        "direction": "descending"
                    }
                ]
            }
            
            logger.info("Filtering for Format='Carousel' AND Status='Brainstorming'")
            
            response = self.client.databases.query(**query_params)
            
            pages = response.get("results", [])
            logger.info(f"Found {len(pages)} Carousel records with Brainstorming status")
            
            return pages
            
        except APIResponseError as e:
            error_msg = f"Failed to query brainstorming carousels: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error querying brainstorming carousels: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg)
    
    async def query_client_projects(self, database_id: str, project_name: str) -> list:
        """Query Client Project Database for name matching
        
        Args:
            database_id: The Client Project Database ID
            project_name: Project name to search for
            
        Returns:
            List of matching project page objects
            
        Raises:
            NotionAPIError: If database query fails
        """
        try:
            logger.info(f"Searching for client project: {project_name}")
            
            # Build query to search for project name in both Name (title) and Client_Project_Name fields
            query_params = {
                "database_id": database_id,
                "filter": {
                    "or": [
                        {
                            "property": "Name",  # Title field
                            "title": {
                                "contains": project_name
                            }
                        },
                        {
                            "property": "Client_Project_Name",  # Rich text field
                            "rich_text": {
                                "contains": project_name
                            }
                        }
                    ]
                },
                "page_size": 10
            }
            
            logger.info(f"Searching Name and Client_Project_Name fields for: '{project_name}'")
            
            response = self.client.databases.query(**query_params)
            
            projects = response.get("results", [])
            logger.info(f"Found {len(projects)} matching client projects")
            
            # If multiple matches, prefer the one with existing system message data
            if len(projects) > 1:
                logger.info("Multiple matches found - prioritizing record with system message data")
                for project in projects:
                    properties = project.get("properties", {})
                    system_message_url = properties.get("System_Message_URL", {}).get("url")
                    system_message_generated = properties.get("System_Message_Generated", {}).get("checkbox", False)
                    
                    if system_message_url and system_message_generated:
                        logger.info(f"Prioritizing project with system message: {project.get('id')}")
                        return [project]  # Return only the one with system message
                
                # If no project has system message, return the first one
                logger.info("No project has system message data, using first match")
                return [projects[0]]
            
            return projects
            
        except APIResponseError as e:
            error_msg = f"Failed to query client projects: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error querying client projects: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg)
    
    async def get_social_media_dashboard_page(self, page_id: str) -> NotionPage:
        """Get Social Media Dashboard page data
        
        Args:
            page_id: The Social Media Dashboard Page ID
            
        Returns:
            NotionPage model with dashboard data
            
        Raises:
            NotionAPIError: If page retrieval fails
        """
        try:
            logger.info(f"Fetching Social Media Dashboard page: {page_id}")
            return await self.get_page(page_id)
        except Exception as e:
            error_msg = f"Failed to retrieve Social Media Dashboard page {page_id}: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg)
    
    def extract_client_name_from_project(self, project_page: dict) -> str:
        """Extract client name from project page
        
        Args:
            project_page: Notion project page object
            
        Returns:
            Client name string
        """
        try:
            properties = project_page.get("properties", {})
            
            # Try different possible property names for client name (based on actual database schema)
            client_name_properties = ["Name", "Client", "Client 1"]
            
            for prop_name in client_name_properties:
                if prop_name in properties:
                    prop = properties[prop_name]
                    prop_type = prop.get("type")
                    
                    if prop_type == "title" and prop.get("title"):
                        return "".join([part.get("plain_text", "") for part in prop["title"]])
                    elif prop_type == "rich_text" and prop.get("rich_text"):
                        return self._extract_rich_text(prop["rich_text"])
                    elif prop_type == "select" and prop.get("select"):
                        return prop["select"].get("name", "")
            
            # Fallback: use page title or first words
            logger.warning("Could not find client name property, using fallback")
            return "Unknown_Client"
            
        except Exception as e:
            logger.warning(f"Error extracting client name: {e}")
            return "Unknown_Client"
    
    async def update_client_project_system_message(
        self,
        project_id: str,
        system_message_file_id: str,
        system_message_url: str,
        client_name: Optional[str] = None
    ) -> bool:
        """Update Client Project Database with system message references
        
        Args:
            project_id: Notion project page ID
            system_message_file_id: Google Drive file ID
            system_message_url: Google Drive file URL
            client_name: Client name to populate in Client_Project_Name field
            
        Returns:
            True if update was successful
            
        Raises:
            NotionAPIError: If update fails
        """
        try:
            logger.info(f"Updating Client Project {project_id} with system message references")
            
            # Get current page to check available properties
            page = self.client.pages.retrieve(page_id=project_id)
            available_properties = page.get("properties", {})
            
            # Build properties update with only available properties
            properties = {}
            
            # Always try to update these as they exist in the database
            if "System_Message_URL" in available_properties:
                properties["System_Message_URL"] = {
                    "url": system_message_url
                }
                logger.info(f"Will update System_Message_URL")
            
            if "System_Message_Generated" in available_properties:
                properties["System_Message_Generated"] = {
                    "checkbox": True
                }
                logger.info(f"Will update System_Message_Generated")
            
            # Update Content Engine Profile Updated checkbox 
            if "Content Engine Profile Updated" in available_properties:
                properties["Content Engine Profile Updated"] = {
                    "checkbox": True
                }
                logger.info(f"Will update Content Engine Profile Updated")
            
            # Update Client_Project_Name field with extracted client name
            if "Client_Project_Name" in available_properties and client_name:
                properties["Client_Project_Name"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": client_name
                            }
                        }
                    ]
                }
                logger.info(f"Will update Client_Project_Name with: {client_name}")
            
            # Optional properties - only add if they exist
            if "System_Message_File_ID" in available_properties:
                # Try to determine the property type
                prop_type = available_properties["System_Message_File_ID"].get("type")
                if prop_type == "rich_text":
                    properties["System_Message_File_ID"] = {
                        "rich_text": [
                            {
                                "text": {
                                    "content": system_message_file_id
                                }
                            }
                        ]
                    }
                elif prop_type == "url":
                    # If it's a URL field, we'd need the full Google Drive URL, not just file ID
                    pass
                logger.info(f"Will update System_Message_File_ID ({prop_type})")
            else:
                logger.warning(f"System_Message_File_ID property not found, skipping")
            
            if "Last_System_Message_Update" in available_properties:
                from datetime import datetime
                properties["Last_System_Message_Update"] = {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                }
                logger.info(f"Will update Last_System_Message_Update")
            else:
                logger.warning(f"Last_System_Message_Update property not found, skipping")
            
            if not properties:
                logger.warning(f"No updatable properties found for project {project_id}")
                return False
            
            # Update the page
            self.client.pages.update(
                page_id=project_id,
                properties=properties
            )
            
            logger.info(f"Successfully updated Client Project {project_id} with {len(properties)} properties")
            return True
            
        except APIResponseError as e:
            error_msg = f"Failed to update Client Project {project_id}: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg, page_id=project_id)
        except Exception as e:
            error_msg = f"Unexpected error updating Client Project {project_id}: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg, page_id=project_id)
    
    async def update_client_project_usage_tracking(
        self,
        project_id: str,
        carousel_page_id: str,
        carousel_title: str
    ) -> bool:
        """Update Client Project Database to track system message usage
        
        Args:
            project_id: Client Project Database page ID
            carousel_page_id: Content Engine DB page ID that used the system message
            carousel_title: Title of the carousel that used the system message
            
        Returns:
            True if update was successful
            
        Raises:
            NotionAPIError: If update fails
        """
        try:
            logger.info(f"Updating Client Project {project_id} usage tracking for carousel: {carousel_title}")
            
            from datetime import datetime
            
            # Get current page to check available properties
            page = self.client.pages.retrieve(page_id=project_id)
            available_properties = page.get("properties", {})
            
            # Build properties update for usage tracking
            properties = {}
            
            # Update Last System Message Usage timestamp
            if "Last_System_Message_Usage" in available_properties:
                properties["Last_System_Message_Usage"] = {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                }
                logger.info("Will update Last_System_Message_Usage")
            else:
                logger.warning("Last_System_Message_Usage field not found, skipping")
            
            # Update Usage Count (increment by 1)
            if "System_Message_Usage_Count" in available_properties:
                # Get current count
                current_count_prop = available_properties.get("System_Message_Usage_Count", {})
                current_count = 0
                
                if current_count_prop.get("type") == "number":
                    current_count = current_count_prop.get("number", 0) or 0
                
                properties["System_Message_Usage_Count"] = {
                    "number": current_count + 1
                }
                logger.info(f"Will update System_Message_Usage_Count from {current_count} to {current_count + 1}")
            else:
                logger.warning("System_Message_Usage_Count field not found, skipping")
            
            # Update Last Used For field with carousel title
            if "Last_Used_For" in available_properties:
                properties["Last_Used_For"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": carousel_title
                            }
                        }
                    ]
                }
                logger.info(f"Will update Last_Used_For with: {carousel_title}")
            else:
                logger.warning("Last_Used_For field not found, skipping")
            
            if not properties:
                logger.warning(f"No updatable usage tracking properties found for project {project_id}")
                return False
            
            # Update the page
            self.client.pages.update(
                page_id=project_id,
                properties=properties
            )
            
            logger.info(f"Successfully updated client project usage tracking: {project_id}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to update client project usage tracking {project_id}: {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg)
    
    async def _create_client_project(self, database_id: str, project_name: str) -> dict:
        """Create a new client project in the Client Project Database
        
        Args:
            database_id: Client Project Database ID
            project_name: Name for the new project
            
        Returns:
            Created project page object
            
        Raises:
            NotionAPIError: If project creation fails
        """
        try:
            logger.info(f"Creating new client project: {project_name}")
            
            # Prepare properties for new client project
            properties = {
                "Name": {  # Title field
                    "title": [
                        {
                            "text": {
                                "content": project_name
                            }
                        }
                    ]
                },
                "Client_Project_Name": {  # Rich text field
                    "rich_text": [
                        {
                            "text": {
                                "content": project_name
                            }
                        }
                    ]
                }
            }
            
            # Create the page
            response = self.client.pages.create(
                parent={"database_id": database_id},
                properties=properties
            )
            
            logger.info(f"Successfully created client project: {response.get('id')}")
            return response
            
        except APIResponseError as e:
            error_msg = f"Failed to create client project '{project_name}': {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error creating client project '{project_name}': {e}"
            logger.error(error_msg)
            raise NotionAPIError(error_msg)