"""
Document processing service for client uploads
"""

import logging
import tempfile
from typing import Dict, Optional, Tuple
from io import BytesIO
import PyPDF2
from docx import Document
import pdfplumber

from ..core.config import config
from ..core.models import DocumentType
from ..core.exceptions import ContentProcessingError

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Service for extracting content from uploaded client documents"""
    
    def __init__(self):
        """Initialize document processor"""
        self.max_file_size_mb = config.max_file_size_mb
        self.allowed_file_types = config.allowed_file_types
        
    async def process_document(
        self, 
        file_data: bytes, 
        filename: str, 
        document_type: DocumentType
    ) -> Tuple[str, int]:
        """Process uploaded document and extract content
        
        Args:
            file_data: Document file data as bytes
            filename: Original filename
            document_type: Type of document being processed
            
        Returns:
            Tuple of (extracted_content, file_size_bytes)
            
        Raises:
            ContentProcessingError: If document processing fails
        """
        try:
            logger.info(f"Processing document: {filename}, type: {document_type.value}")
            
            file_size_bytes = len(file_data)
            
            # Validate file size
            max_size_bytes = self.max_file_size_mb * 1024 * 1024
            if file_size_bytes > max_size_bytes:
                raise ContentProcessingError(
                    f"File too large: {file_size_bytes / (1024*1024):.2f}MB. Max allowed: {self.max_file_size_mb}MB"
                )
            
            # Validate file type
            file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
            if file_extension not in self.allowed_file_types:
                raise ContentProcessingError(
                    f"Unsupported file type: {file_extension}. Allowed: {', '.join(self.allowed_file_types)}"
                )
            
            # Extract content based on file type
            if file_extension == 'pdf':
                content = await self._extract_from_pdf(file_data)
            elif file_extension in ['docx', 'doc']:
                content = await self._extract_from_docx(file_data)
            elif file_extension in ['txt', 'md']:
                content = await self._extract_from_text(file_data)
            else:
                raise ContentProcessingError(f"Unsupported file type: {file_extension}")
            
            # Validate extracted content
            if not content.strip():
                raise ContentProcessingError("No text content could be extracted from the document")
            
            logger.info(f"Successfully extracted {len(content)} characters from {filename}")
            return content.strip(), file_size_bytes
            
        except Exception as e:
            error_msg = f"Failed to process document {filename}: {e}"
            logger.error(error_msg)
            raise ContentProcessingError(error_msg)
    
    async def _extract_from_pdf(self, file_data: bytes) -> str:
        """Extract text from PDF using pdfplumber (more reliable than PyPDF2)
        
        Args:
            file_data: PDF file data as bytes
            
        Returns:
            Extracted text content
        """
        try:
            content_parts = []
            
            with BytesIO(file_data) as pdf_buffer:
                with pdfplumber.open(pdf_buffer) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        try:
                            text = page.extract_text()
                            if text:
                                content_parts.append(text)
                                logger.debug(f"Extracted text from PDF page {page_num}")
                            else:
                                logger.warning(f"No text found on PDF page {page_num}")
                        except Exception as e:
                            logger.warning(f"Error extracting text from PDF page {page_num}: {e}")
                            continue
            
            if not content_parts:
                # Fallback to PyPDF2
                logger.info("pdfplumber failed, trying PyPDF2 fallback")
                return await self._extract_from_pdf_pypdf2(file_data)
            
            return '\n\n'.join(content_parts)
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            # Try PyPDF2 as fallback
            return await self._extract_from_pdf_pypdf2(file_data)
    
    async def _extract_from_pdf_pypdf2(self, file_data: bytes) -> str:
        """Fallback PDF extraction using PyPDF2
        
        Args:
            file_data: PDF file data as bytes
            
        Returns:
            Extracted text content
        """
        try:
            content_parts = []
            
            with BytesIO(file_data) as pdf_buffer:
                pdf_reader = PyPDF2.PdfReader(pdf_buffer)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        text = page.extract_text()
                        if text:
                            content_parts.append(text)
                            logger.debug(f"Extracted text from PDF page {page_num} using PyPDF2")
                    except Exception as e:
                        logger.warning(f"Error extracting text from PDF page {page_num} using PyPDF2: {e}")
                        continue
            
            if not content_parts:
                raise ContentProcessingError("Could not extract any text from PDF using either method")
            
            return '\n\n'.join(content_parts)
            
        except Exception as e:
            raise ContentProcessingError(f"PyPDF2 extraction failed: {e}")
    
    async def _extract_from_docx(self, file_data: bytes) -> str:
        """Extract text from Word document
        
        Args:
            file_data: DOCX file data as bytes
            
        Returns:
            Extracted text content
        """
        try:
            content_parts = []
            
            with BytesIO(file_data) as docx_buffer:
                doc = Document(docx_buffer)
                
                # Extract text from paragraphs
                for paragraph in doc.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        content_parts.append(text)
                
                # Extract text from tables
                for table in doc.tables:
                    for row in table.rows:
                        row_text = []
                        for cell in row.cells:
                            cell_text = cell.text.strip()
                            if cell_text:
                                row_text.append(cell_text)
                        if row_text:
                            content_parts.append(' | '.join(row_text))
            
            if not content_parts:
                raise ContentProcessingError("No text content found in Word document")
            
            return '\n\n'.join(content_parts)
            
        except Exception as e:
            raise ContentProcessingError(f"Word document extraction failed: {e}")
    
    async def _extract_from_text(self, file_data: bytes) -> str:
        """Extract text from plain text file
        
        Args:
            file_data: Text file data as bytes
            
        Returns:
            Extracted text content
        """
        try:
            # Try UTF-8 first, then common encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    content = file_data.decode(encoding)
                    logger.debug(f"Successfully decoded text file using {encoding}")
                    return content
                except UnicodeDecodeError:
                    continue
            
            raise ContentProcessingError("Could not decode text file with any common encoding")
            
        except Exception as e:
            raise ContentProcessingError(f"Text file extraction failed: {e}")
    
    def generate_system_message(self, extracted_content: Dict[str, str]) -> str:
        """Generate system message for OpenAI from extracted document content
        
        Args:
            extracted_content: Dictionary mapping document types to their content
            
        Returns:
            System message string for OpenAI API
        """
        try:
            logger.info("Generating system message from client documents")
            
            system_message_parts = [
                "You are GPT-5, enhanced with 20 years of proven social media marketing expertise.",
                "You understand exactly what makes people stop scrolling, engage emotionally, and take action.",
                "Use the following client-specific information to create content that matches their unique voice and targets their ideal audience:"
            ]
            
            # Add client profile information
            if DocumentType.CLIENT_PROFILE.value in extracted_content:
                profile_content = extracted_content[DocumentType.CLIENT_PROFILE.value]
                system_message_parts.extend([
                    "",
                    "CLIENT PROFILE:",
                    profile_content,
                    ""
                ])
            
            # Add ideal client profile information
            if DocumentType.CONTENT_ICP.value in extracted_content:
                icp_content = extracted_content[DocumentType.CONTENT_ICP.value]
                system_message_parts.extend([
                    "IDEAL CLIENT PROFILE:",
                    icp_content,
                    ""
                ])
            
            # Add voice and style guide information
            if DocumentType.VOICE_STYLE_GUIDE.value in extracted_content:
                voice_content = extracted_content[DocumentType.VOICE_STYLE_GUIDE.value]
                system_message_parts.extend([
                    "VOICE & STYLE GUIDE:",
                    voice_content,
                    ""
                ])
            
            # Add instructions for content creation
            system_message_parts.extend([
                "CONTENT CREATION INSTRUCTIONS:",
                "- Create content that aligns perfectly with the client's voice and tone",
                "- Target the specific ideal client profile described above",
                "- Use language patterns and messaging that resonate with the target audience",
                "- Incorporate the brand personality and values outlined in the client profile",
                "- Ensure all content feels authentic to this specific client's brand",
                "- Create connected storytelling that builds engagement across slides",
                ""
            ])
            
            system_message = "\n".join(system_message_parts)
            
            logger.info(f"Generated system message with {len(system_message)} characters")
            return system_message
            
        except Exception as e:
            error_msg = f"Failed to generate system message: {e}"
            logger.error(error_msg)
            raise ContentProcessingError(error_msg)
    
    def validate_file_upload(self, filename: str, file_size: int) -> Tuple[bool, str]:
        """Validate uploaded file before processing
        
        Args:
            filename: Original filename
            file_size: File size in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        max_size_bytes = self.max_file_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"File too large: {file_size / (1024*1024):.2f}MB. Max allowed: {self.max_file_size_mb}MB"
        
        # Check file extension
        file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
        if file_extension not in self.allowed_file_types:
            return False, f"Unsupported file type: {file_extension}. Allowed: {', '.join(self.allowed_file_types)}"
        
        # Check filename
        if not filename.strip():
            return False, "Filename cannot be empty"
        
        return True, ""