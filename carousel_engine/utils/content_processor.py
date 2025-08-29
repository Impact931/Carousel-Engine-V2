"""
Content processing utilities for Carousel Engine v2
"""

import logging
import re
from typing import List, Tuple
from ..core.models import CarouselSlide
from ..core.config import config
from ..core.exceptions import ContentProcessingError

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Content processing utilities for carousel generation"""
    
    def __init__(self):
        """Initialize content processor"""
        self.max_slides = config.max_carousel_slides
        self.lines_per_slide = config.lines_per_slide
    
    def process_content_to_slides(
        self, 
        title: str, 
        content: str,
        optimized_content: List[str] = None
    ) -> List[CarouselSlide]:
        """Process content into carousel slides
        
        Args:
            title: Content title
            content: Raw content text
            optimized_content: Pre-optimized slide content from OpenAI
            
        Returns:
            List of CarouselSlide objects
            
        Raises:
            ContentProcessingError: If content processing fails
        """
        try:
            logger.info(f"Processing content into slides. Title: {title}")
            
            slides = []
            
            # NO title slide - jump straight to content as per requirements
            
            # Process content slides  
            if optimized_content:
                # Use AI-optimized content (4-7 slides as determined by AI)
                for i, slide_text in enumerate(optimized_content):
                    content_slide = CarouselSlide(
                        slide_number=i + 1,
                        title=None,
                        content=slide_text.strip(),
                        is_title_slide=False
                    )
                    slides.append(content_slide)
            else:
                # Fallback to manual segmentation
                content_slides = self._segment_content_manually(content)
                for i, slide_text in enumerate(content_slides):
                    content_slide = CarouselSlide(
                        slide_number=i + 1,
                        title=None,
                        content=slide_text.strip(),
                        is_title_slide=False
                    )
                    slides.append(content_slide)
            
            logger.info(f"Successfully created {len(slides)} content slides")
            return slides
            
        except Exception as e:
            error_msg = f"Failed to process content into slides: {e}"
            logger.error(error_msg)
            raise ContentProcessingError(error_msg, content=content)
    
    def _segment_content_manually(self, content: str) -> List[str]:
        """Manually segment content into slides (fallback method)
        
        Args:
            content: Raw content text
            
        Returns:
            List of slide text strings
        """
        try:
            # Clean and normalize content
            content = self._clean_content(content)
            
            # Split into paragraphs
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            slides = []
            current_slide_lines = []
            
            for paragraph in paragraphs:
                # Split paragraph into sentences
                sentences = self._split_into_sentences(paragraph)
                
                for sentence in sentences:
                    # Check if adding this sentence would exceed line limit
                    if len(current_slide_lines) >= self.lines_per_slide:
                        # Save current slide and start new one
                        if current_slide_lines:
                            slides.append('\n'.join(current_slide_lines))
                        current_slide_lines = [sentence]
                    else:
                        current_slide_lines.append(sentence)
                    
                    # Stop if we've reached max slides
                    if len(slides) >= self.max_slides:
                        break
                
                if len(slides) >= self.max_slides:
                    break
            
            # Add remaining lines as final slide
            if current_slide_lines and len(slides) < self.max_slides:
                slides.append('\n'.join(current_slide_lines))
            
            return slides[:self.max_slides]
            
        except Exception as e:
            logger.error(f"Error in manual content segmentation: {e}")
            # Fallback: just split by lines
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            slides = []
            
            for i in range(0, len(lines), self.lines_per_slide):
                slide_lines = lines[i:i + self.lines_per_slide]
                if slide_lines:
                    slides.append('\n'.join(slide_lines))
                if len(slides) >= self.max_slides:
                    break
            
            return slides
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content text
        
        Args:
            content: Raw content
            
        Returns:
            Cleaned content
        """
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove markdown formatting (basic)
        content = re.sub(r'#{1,6}\s*', '', content)  # Headers
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Bold
        content = re.sub(r'\*(.*?)\*', r'\1', content)  # Italic
        content = re.sub(r'`(.*?)`', r'\1', content)  # Code
        
        # Clean up bullet points
        content = re.sub(r'^\s*[•\-\*]\s*', '• ', content, flags=re.MULTILINE)
        
        # Remove excessive punctuation
        content = re.sub(r'\.{2,}', '.', content)
        content = re.sub(r'\!{2,}', '!', content)
        content = re.sub(r'\?{2,}', '?', content)
        
        return content.strip()
    
    def _split_into_sentences(self, paragraph: str) -> List[str]:
        """Split paragraph into sentences
        
        Args:
            paragraph: Paragraph text
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting (could be improved with NLP)
        sentences = re.split(r'[.!?]+\s+', paragraph)
        
        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Ensure sentences end with punctuation
        for i, sentence in enumerate(sentences):
            if not sentence.endswith(('.', '!', '?')):
                sentences[i] = sentence + '.'
        
        return sentences
    
    def validate_slide_content(self, slide: CarouselSlide) -> Tuple[bool, str]:
        """Validate slide content meets requirements
        
        Args:
            slide: CarouselSlide to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            content = slide.content
            
            # Check if content is empty
            if not content or not content.strip():
                return False, "Slide content is empty"
            
            # Check line count (for non-title slides) - more flexible for engaging content
            if not slide.is_title_slide:
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                # Allow more flexibility for better storytelling (up to 5 lines for engaging content)
                max_allowed = 5  # Allow up to 5 lines for compelling social media content
                if len(lines) > max_allowed:
                    return False, f"Too many lines ({len(lines)}). Maximum: {max_allowed}"
            
            # Check content length (reasonable limits for social media)
            if len(content) > 2000:  # More reasonable limit for social media
                return False, "Content too long for social media slide"
            
            # Check for problematic characters
            if any(ord(char) > 65535 for char in content):
                return False, "Content contains unsupported characters"
            
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def optimize_for_social_media(self, content: str) -> str:
        """Optimize content for social media engagement
        
        Args:
            content: Raw content
            
        Returns:
            Optimized content
        """
        try:
            # Add emoji support (basic patterns)
            content = re.sub(r'\btip\b', '💡 tip', content, flags=re.IGNORECASE)
            content = re.sub(r'\bimportant\b', '⚠️ important', content, flags=re.IGNORECASE)
            content = re.sub(r'\bsuccess\b', '✅ success', content, flags=re.IGNORECASE)
            
            # Enhance call-to-action phrases
            content = re.sub(r'\blearn more\b', 'Learn More →', content, flags=re.IGNORECASE)
            content = re.sub(r'\bget started\b', 'Get Started 🚀', content, flags=re.IGNORECASE)
            
            # Improve readability
            content = re.sub(r'(\d+)', r'**\1**', content)  # Bold numbers
            
            return content
            
        except Exception as e:
            logger.error(f"Error optimizing content for social media: {e}")
            return content  # Return original if optimization fails