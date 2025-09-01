"""
Google Drive API service for Carousel Engine v2
"""

import json
import logging
import os
from io import BytesIO
from typing import List, Optional, Tuple
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import GoogleAuthError
import pickle

from ..core.config import config
from ..core.exceptions import GoogleDriveError

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Service for interacting with Google Drive API"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """Initialize Google Drive service with OAuth
        
        Args:
            client_id: OAuth client ID, defaults to config value
            client_secret: OAuth client secret, defaults to config value
        """
        self.client_id = client_id or config.google_oauth_client_id
        self.client_secret = client_secret or config.google_oauth_client_secret
        self.refresh_token = config.google_refresh_token
        self.token_file = 'google_drive_token.pickle'
        self.service = None  # Lazy initialization
        logger.info("Google Drive service created (OAuth will be initialized on first use)")
    
    def _ensure_service_initialized(self):
        """Initialize the Google Drive service if not already done"""
        if self.service is None:
            if not self.client_id or not self.client_secret:
                raise GoogleDriveError(
                    "Google OAuth credentials not configured. "
                    "Please set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables."
                )
            
            try:
                credentials = self._get_credentials()
                self.service = build('drive', 'v3', credentials=credentials)
                
                # Test the service with a simple call to verify authentication
                try:
                    test_result = self.service.about().get(fields='user').execute()
                    if test_result is None:
                        raise GoogleDriveError("Google Drive API test call returned None - authentication failed")
                    logger.info(f"Google Drive service initialized and authenticated successfully as: {test_result.get('user', {}).get('emailAddress', 'unknown')}")
                except Exception as auth_test_error:
                    self.service = None  # Reset service to prevent invalid state
                    raise GoogleDriveError(f"Google Drive authentication test failed: {auth_test_error}")
                    
            except Exception as e:
                error_msg = f"Failed to initialize Google Drive service: {e}"
                logger.error(error_msg)
                self.service = None  # Ensure service is None on failure
                raise GoogleDriveError(error_msg)
    
    def _get_credentials(self) -> Credentials:
        """Get or refresh OAuth credentials"""
        credentials = None
        
        # If we have a refresh token from environment, create credentials directly
        if self.refresh_token:
            logger.info("Using refresh token from environment variables")
            credentials = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                client_id=self.client_id,
                client_secret=self.client_secret,
                token_uri="https://accounts.google.com/o/oauth2/token"
            )
            
            # Refresh to get access token
            try:
                credentials.refresh(Request())
                logger.info("Successfully refreshed credentials using environment refresh token")
                
                # Save the credentials for future use
                try:
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(credentials, token)
                    logger.info(f"Saved credentials to {self.token_file}")
                except Exception as e:
                    logger.warning(f"Failed to save credentials: {e}")
                
                return credentials
            except Exception as e:
                logger.error(f"Failed to refresh credentials from environment: {e}")
                credentials = None
        
        # Load existing token file if no refresh token in environment
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    credentials = pickle.load(token)
                logger.info("Loaded credentials from token file")
            except Exception as e:
                logger.warning(f"Failed to load token file: {e}")
                credentials = None
        
        # If no valid credentials are available, initiate OAuth flow
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    logger.info("Refreshed Google OAuth credentials from token file")
                    
                    # Save refreshed credentials
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(credentials, token)
                        
                except Exception as e:
                    logger.warning(f"Failed to refresh credentials: {e}")
                    credentials = None
            
            if not credentials:
                raise GoogleDriveError(
                    "Google OAuth credentials not found or expired. "
                    "Please ensure GOOGLE_REFRESH_TOKEN environment variable is set, "
                    "or run the OAuth setup process to create a token file."
                )
        
        return credentials
    
    def setup_oauth_flow(self, redirect_uri: str = 'http://localhost:8080/callback'):
        """Setup OAuth flow for initial authentication
        
        Args:
            redirect_uri: OAuth redirect URI
            
        Returns:
            Authorization URL for user to visit
        """
        try:
            flow = Flow.from_client_config({
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            }, scopes=self.SCOPES)
            
            flow.redirect_uri = redirect_uri
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            logger.info("OAuth flow setup complete")
            return auth_url, flow
            
        except Exception as e:
            error_msg = f"Failed to setup OAuth flow: {e}"
            logger.error(error_msg)
            raise GoogleDriveError(error_msg)
    
    async def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Tuple[str, str]:
        """Create a new folder in Google Drive
        
        Args:
            folder_name: Name of the folder to create
            parent_folder_id: ID of parent folder, None for root
            
        Returns:
            Tuple of (folder_id, folder_url)
            
        Raises:
            GoogleDriveError: If folder creation fails
        """
        try:
            self._ensure_service_initialized()
            logger.info(f"Creating Google Drive folder: {folder_name}")
            
            # Prepare folder metadata
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            # Set parent folder if specified
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            
            # Create folder
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id, webViewLink'
            ).execute()
            
            folder_id = folder.get('id')
            folder_url = folder.get('webViewLink')
            
            # Make folder publicly viewable
            await self._make_folder_public(folder_id)
            
            logger.info(f"Successfully created folder {folder_name} with ID: {folder_id}")
            return folder_id, folder_url
            
        except Exception as e:
            error_msg = f"Failed to create Google Drive folder {folder_name}: {e}"
            logger.error(error_msg)
            raise GoogleDriveError(error_msg, folder_id=parent_folder_id)
    
    async def upload_image(
        self, 
        image_data: bytes, 
        filename: str, 
        folder_id: str,
        mime_type: str = 'image/png'
    ) -> Tuple[str, str]:
        """Upload an image to Google Drive
        
        Args:
            image_data: Image data as bytes
            filename: Name for the uploaded file
            folder_id: ID of the folder to upload to
            mime_type: MIME type of the image
            
        Returns:
            Tuple of (file_id, file_url)
            
        Raises:
            GoogleDriveError: If upload fails
        """
        try:
            logger.info(f"Uploading image {filename} to folder {folder_id}")
            
            # Prepare file metadata
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            # Create media upload
            media = MediaIoBaseUpload(
                BytesIO(image_data),
                mimetype=mime_type,
                resumable=True
            )
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            file_id = file.get('id')
            file_url = file.get('webViewLink')
            
            # Make file publicly viewable
            await self._make_file_public(file_id)
            
            logger.info(f"Successfully uploaded image {filename} with ID: {file_id}")
            return file_id, file_url
            
        except Exception as e:
            error_msg = f"Failed to upload image {filename} to Google Drive: {e}"
            logger.error(error_msg)
            raise GoogleDriveError(error_msg, folder_id=folder_id)
    
    async def upload_multiple_images(
        self, 
        images: List[Tuple[bytes, str]], 
        folder_id: str
    ) -> List[Tuple[str, str]]:
        """Upload multiple images to Google Drive
        
        Args:
            images: List of (image_data, filename) tuples
            folder_id: ID of the folder to upload to
            
        Returns:
            List of (file_id, file_url) tuples
            
        Raises:
            GoogleDriveError: If any upload fails
        """
        results = []
        
        for image_data, filename in images:
            try:
                file_id, file_url = await self.upload_image(image_data, filename, folder_id)
                results.append((file_id, file_url))
            except GoogleDriveError:
                # Re-raise to stop processing on first failure
                raise
            except Exception as e:
                error_msg = f"Failed to upload image {filename}: {e}"
                logger.error(error_msg)
                raise GoogleDriveError(error_msg, folder_id=folder_id)
        
        logger.info(f"Successfully uploaded {len(results)} images to folder {folder_id}")
        return results
    
    async def get_folder_info(self, folder_id: str) -> Optional[dict]:
        """Get information about a Google Drive folder
        
        Args:
            folder_id: ID of the folder
            
        Returns:
            Folder information dict or None if not found
            
        Raises:
            GoogleDriveError: If folder access fails
        """
        try:
            logger.info(f"Getting info for folder: {folder_id}")
            
            folder = self.service.files().get(
                fileId=folder_id,
                fields='id, name, webViewLink, parents, createdTime, modifiedTime'
            ).execute()
            
            return folder
            
        except Exception as e:
            if "404" in str(e).lower() or "not found" in str(e).lower():
                logger.warning(f"Folder {folder_id} not found")
                return None
            
            error_msg = f"Failed to get folder info for {folder_id}: {e}"
            logger.error(error_msg)
            raise GoogleDriveError(error_msg, folder_id=folder_id)
    
    async def _make_folder_public(self, folder_id: str) -> bool:
        """Make a folder publicly viewable
        
        Args:
            folder_id: ID of the folder
            
        Returns:
            True if successful
            
        Raises:
            GoogleDriveError: If permission setting fails
        """
        try:
            # Set public read permission
            permission = {
                'role': 'reader',
                'type': 'anyone'
            }
            
            self.service.permissions().create(
                fileId=folder_id,
                body=permission
            ).execute()
            
            logger.info(f"Made folder {folder_id} publicly viewable")
            return True
            
        except Exception as e:
            error_msg = f"Failed to make folder {folder_id} public: {e}"
            logger.error(error_msg)
            raise GoogleDriveError(error_msg, folder_id=folder_id)
    
    async def _make_file_public(self, file_id: str) -> bool:
        """Make a file publicly viewable
        
        Args:
            file_id: ID of the file
            
        Returns:
            True if successful
            
        Raises:
            GoogleDriveError: If permission setting fails
        """
        try:
            # Set public read permission
            permission = {
                'role': 'reader',
                'type': 'anyone'
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            logger.info(f"Made file {file_id} publicly viewable")
            return True
            
        except Exception as e:
            error_msg = f"Failed to make file {file_id} public: {e}"
            logger.error(error_msg)
            raise GoogleDriveError(error_msg)
    
    async def create_client_folder(self, client_name: str, parent_folder_id: str) -> Tuple[str, str]:
        """Create client folder with serial number in target directory
        
        Args:
            client_name: Client name for folder naming
            parent_folder_id: Parent folder ID where client folder will be created
            
        Returns:
            Tuple of (folder_id, folder_url)
            
        Raises:
            GoogleDriveError: If folder creation fails
        """
        try:
            logger.info(f"Creating client folder for: {client_name}")
            
            # Get existing folders to determine serial number
            existing_folders = await self.list_folders(parent_folder_id)
            serial_number = self._generate_serial_number(client_name, existing_folders)
            
            # Create folder name with serial number
            folder_name = f"{client_name}_{serial_number:03d}"
            
            # Create the folder
            folder_id, folder_url = await self.create_folder(folder_name, parent_folder_id)
            
            logger.info(f"Successfully created client folder: {folder_name} with ID: {folder_id}")
            return folder_id, folder_url
            
        except Exception as e:
            error_msg = f"Failed to create client folder for {client_name}: {e}"
            logger.error(error_msg)
            raise GoogleDriveError(error_msg)
    
    async def list_folders(self, parent_folder_id: str) -> List[dict]:
        """List folders within a parent folder
        
        Args:
            parent_folder_id: Parent folder ID to search in
            
        Returns:
            List of folder information dictionaries
            
        Raises:
            GoogleDriveError: If listing fails
        """
        try:
            logger.info(f"DEBUG: Starting list_folders method for parent: {parent_folder_id}")
            self._ensure_service_initialized()
            logger.info(f"DEBUG: Service initialized, listing folders in parent: {parent_folder_id}")
            
            query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, createdTime, modifiedTime)",
                orderBy="name"
            ).execute()
            
            logger.info(f"Google Drive API response: {results}")
            if results is None:
                raise GoogleDriveError(f"Google Drive API returned None for query: {query}")
            
            if results is None:
                logger.error(f"CRITICAL: Google Drive API returned None - check authentication")
                raise GoogleDriveError(f"Google Drive API returned None for query: {query} - authentication may be invalid")
            folders = results.get('files', [])
            logger.info(f"Found {len(folders)} folders in parent {parent_folder_id}")
            
            return folders
            
        except Exception as e:
            error_msg = f"Failed to list folders in {parent_folder_id}: {e}"
            logger.error(error_msg)
            raise GoogleDriveError(error_msg, folder_id=parent_folder_id)
    
    async def upload_client_documents(
        self, 
        documents: List[Tuple[bytes, str, str]], 
        folder_id: str
    ) -> List[Tuple[str, str]]:
        """Upload multiple client documents to specific folder
        
        Args:
            documents: List of (document_data, filename, mime_type) tuples
            folder_id: Target folder ID
            
        Returns:
            List of (file_id, file_url) tuples
            
        Raises:
            GoogleDriveError: If upload fails
        """
        try:
            logger.info(f"Uploading {len(documents)} client documents to folder {folder_id}")
            
            results = []
            
            for doc_data, filename, mime_type in documents:
                file_id, file_url = await self._upload_file(
                    doc_data,
                    filename,
                    mime_type,
                    folder_id
                )
                results.append((file_id, file_url))
                logger.info(f"Successfully uploaded document {filename} with ID: {file_id}")
            
            logger.info(f"Successfully uploaded {len(results)} documents to folder {folder_id}")
            return results
            
        except Exception as e:
            error_msg = f"Failed to upload client documents to folder {folder_id}: {e}"
            logger.error(error_msg)
            raise GoogleDriveError(error_msg, folder_id=folder_id)
    
    async def _upload_file(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str,
        folder_id: str
    ) -> Tuple[str, str]:
        """Upload a file to Google Drive
        
        Args:
            file_data: File data as bytes
            filename: Name for the file
            mime_type: MIME type of the file
            folder_id: ID of the folder to upload to
            
        Returns:
            Tuple of (file_id, file_url)
            
        Raises:
            GoogleDriveError: If upload fails
        """
        try:
            # Create file metadata
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            # Create media upload
            media = MediaIoBaseUpload(
                BytesIO(file_data),
                mimetype=mime_type,
                resumable=True
            )
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            file_id = file.get('id')
            file_url = file.get('webViewLink')
            
            # Make file publicly viewable
            await self._make_file_public(file_id)
            
            logger.info(f"Successfully uploaded file {filename} with ID: {file_id}")
            return file_id, file_url
            
        except Exception as e:
            error_msg = f"Failed to upload file {filename} to Google Drive: {e}"
            logger.error(error_msg)
            raise GoogleDriveError(error_msg, folder_id=folder_id)
    
    def _generate_serial_number(self, client_name: str, existing_folders: List[dict]) -> int:
        """Generate serial number for client folder
        
        Args:
            client_name: Client name
            existing_folders: List of existing folders in parent directory
            
        Returns:
            Next available serial number
        """
        try:
            # Find existing folders with same client name pattern
            client_pattern = f"{client_name}_"
            existing_numbers = []
            
            for folder in existing_folders:
                folder_name = folder.get('name', '')
                if folder_name.startswith(client_pattern):
                    # Extract number from folder name (e.g., "ClientName_001" -> 1)
                    try:
                        number_part = folder_name[len(client_pattern):]
                        if number_part.isdigit():
                            existing_numbers.append(int(number_part))
                    except ValueError:
                        continue
            
            # Return next available number
            if not existing_numbers:
                return 1
            
            return max(existing_numbers) + 1
            
        except Exception as e:
            logger.warning(f"Error generating serial number for {client_name}: {e}")
            return 1
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type based on file extension
        
        Args:
            filename: File name with extension
            
        Returns:
            MIME type string
        """
        file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        mime_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'txt': 'text/plain',
            'md': 'text/markdown'
        }
        
        return mime_types.get(file_extension, 'application/octet-stream')
    
    async def upload_system_message(
        self, 
        system_message: str, 
        client_name: str, 
        folder_id: str
    ) -> Tuple[str, str]:
        """Upload client system message as text file to Google Drive
        
        Args:
            system_message: Generated system message content
            client_name: Client name for filename
            folder_id: Target folder ID
            
        Returns:
            Tuple of (file_id, file_url)
            
        Raises:
            GoogleDriveError: If upload fails
        """
        try:
            logger.info(f"Uploading system message for client: {client_name}")
            
            # Create filename with timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{client_name.replace(' ', '_')}_system_message_{timestamp}.txt"
            
            # Convert system message to bytes
            system_message_bytes = system_message.encode('utf-8')
            
            # Upload as text file
            file_id, file_url = await self._upload_file(
                system_message_bytes,
                filename,
                'text/plain',
                folder_id
            )
            
            logger.info(f"Successfully uploaded system message: {filename} with ID: {file_id}")
            return file_id, file_url
            
        except Exception as e:
            error_msg = f"Failed to upload system message for {client_name}: {e}"
            logger.error(error_msg)
            raise GoogleDriveError(error_msg, folder_id=folder_id)
    
    async def download_text_file(self, file_id: str) -> str:
        """Download text content from Google Drive file
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File content as string
            
        Raises:
            GoogleDriveError: If download fails
        """
        try:
            logger.info(f"Downloading text file: {file_id}")
            
            # Get file content
            request = self.service.files().get_media(fileId=file_id)
            file_content = request.execute()
            
            # Decode content
            content = file_content.decode('utf-8')
            
            logger.info(f"Successfully downloaded text file: {file_id}, length: {len(content)} chars")
            return content
            
        except Exception as e:
            error_msg = f"Failed to download text file {file_id}: {e}"
            logger.error(error_msg)
            raise GoogleDriveError(error_msg)