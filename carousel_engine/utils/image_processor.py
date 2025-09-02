"""
Image processing utilities for Carousel Engine v2
"""

import logging
from io import BytesIO
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import requests

from ..core.config import config
from ..core.exceptions import ImageProcessingError

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Image processing utilities for carousel generation"""
    
    def __init__(self):
        """Initialize image processor"""
        self.width = config.image_width
        self.height = config.image_height
        
    def create_carousel_slide(
        self,
        background_image_data: bytes,
        text: str,
        is_title_slide: bool = False,
        slide_number: Optional[int] = None
    ) -> bytes:
        """Create a carousel slide with text overlay
        
        Args:
            background_image_data: Background image as bytes
            text: Text to overlay
            is_title_slide: Whether this is a title slide
            slide_number: Slide number for non-title slides
            
        Returns:
            Processed image as bytes
            
        Raises:
            ImageProcessingError: If image processing fails
        """
        try:
            logger.info(f"Creating carousel slide. Title slide: {is_title_slide}")
            
            # Load background image
            background = Image.open(BytesIO(background_image_data))
            
            # Resize to target dimensions
            background = background.resize((self.width, self.height), Image.Resampling.LANCZOS)
            
            # Ensure RGB mode
            if background.mode != 'RGB':
                background = background.convert('RGB')
            
            # Create drawing context
            draw = ImageDraw.Draw(background)
            
            # Add text overlay
            if is_title_slide:
                self._add_title_text(draw, text, self.width, self.height)
            else:
                self._add_content_text(draw, text, self.width, self.height, slide_number)
            
            # Branding removed per user request
            # self._add_branding(draw, self.width, self.height)
            
            # Convert to bytes
            output_buffer = BytesIO()
            background.save(output_buffer, format='PNG', optimize=True)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            error_msg = f"Failed to create carousel slide: {e}"
            logger.error(error_msg)
            raise ImageProcessingError(error_msg)
    
    def _add_title_text(self, draw: ImageDraw.Draw, title: str, width: int, height: int) -> None:
        """Add title text to image
        
        Args:
            draw: PIL ImageDraw object
            title: Title text
            width: Image width
            height: Image height
        """
        try:
            # Load title font
            font_size = min(width, height) // 15  # Responsive font size
            title_font = self._get_font(font_size)
            
            # Text styling for title
            text_color = (255, 255, 255)  # White
            stroke_color = (0, 0, 0)  # Black stroke
            stroke_width = 2
            
            # Calculate text position (centered)
            bbox = draw.textbbox((0, 0), title, font=title_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            # Draw text with stroke
            draw.text(
                (x, y), 
                title, 
                font=title_font, 
                fill=text_color,
                stroke_fill=stroke_color,
                stroke_width=stroke_width,
                anchor="lt"
            )
            
            logger.debug(f"Added title text at position ({x}, {y})")
            
        except Exception as e:
            logger.error(f"Failed to add title text: {e}")
    
    def _add_content_text(
        self, 
        draw: ImageDraw.Draw, 
        content: str, 
        width: int, 
        height: int,
        slide_number: Optional[int] = None
    ) -> None:
        """Add content text to image with semi-opaque white box
        
        Args:
            draw: PIL ImageDraw object
            content: Content text
            width: Image width
            height: Image height
            slide_number: Slide number
        """
        try:
            # Calculate responsive font size - increased for better readability
            font_size = int(width * 0.045)  # Increased from width//18 to 4.5% of image width
            content_font = self._get_lato_font(font_size)
            
            # Text box width should be 90% of total image width
            text_box_width = int(width * 0.9)  # 90% of image width
            text_box_left_margin = int(width * 0.05)  # 5% margin on each side
            
            # Split content into 2-3 lines with optimized wrapping
            lines = self._wrap_text_optimized(content, content_font, text_box_width, max_lines=3)
            
            # Calculate text dimensions with improved line spacing
            line_spacing_multiplier = 1.4  # Increased line height for better readability
            line_height = int((content_font.getmetrics()[0] + content_font.getmetrics()[1]) * line_spacing_multiplier)
            total_text_height = len(lines) * line_height
            
            # Position the text box - 90% width, centered vertically
            box_padding = int(width * 0.03)  # Responsive padding (3% of image width)
            box_width = text_box_width
            box_height = total_text_height + (box_padding * 2)
            
            box_x = text_box_left_margin
            box_y = (height - box_height) // 2
            
            # Create semi-opaque white background box (40% opacity)
            box_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            box_draw = ImageDraw.Draw(box_overlay)
            
            # Draw rounded rectangle with 60% white opacity (255 * 0.6 = 153)
            box_draw.rounded_rectangle(
                [(box_x, box_y), (box_x + box_width, box_y + box_height)],
                radius=20,
                fill=(255, 255, 255, 153)  # White with 60% opacity
            )
            
            # Composite the box overlay onto the main image
            background_image = draw._image
            background_rgba = background_image.convert('RGBA')
            background_rgba = Image.alpha_composite(background_rgba, box_overlay)
            draw._image.paste(background_rgba.convert('RGB'))
            
            # Choose dark text color that complements real estate theme
            text_color = (64, 64, 64)  # Dark gray - readable and warm
            
            # Draw text lines with proper positioning within the 90% width box
            text_y = box_y + box_padding
            for line in lines:
                # Center each line within the 90% width box
                line_width = draw.textlength(line, font=content_font)
                text_x = text_box_left_margin + (text_box_width - line_width) // 2
                
                draw.text(
                    (text_x, text_y),
                    line,
                    font=content_font,
                    fill=text_color
                )
                text_y += line_height
            
            # Add slide number if provided
            if slide_number is not None:
                self._add_slide_number(draw, slide_number, width, height)
            
            logger.debug(f"Added content text with {len(lines)} lines")
            
        except Exception as e:
            logger.error(f"Failed to add content text: {e}")
    
    def _add_slide_number(
        self, 
        draw: ImageDraw.Draw, 
        slide_number: int, 
        width: int, 
        height: int
    ) -> None:
        """Add slide number to image
        
        Args:
            draw: PIL ImageDraw object
            slide_number: Slide number
            width: Image width
            height: Image height
        """
        try:
            # Small font for slide number
            font_size = min(width, height) // 40
            number_font = self._get_font(font_size)
            
            # Position in bottom right
            number_text = str(slide_number)
            bbox = draw.textbbox((0, 0), number_text, font=number_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = width - text_width - 20
            y = height - text_height - 20
            
            # Semi-transparent background
            padding = 5
            draw.rectangle(
                [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
                fill=(0, 0, 0, 128)
            )
            
            # Draw number
            draw.text((x, y), number_text, font=number_font, fill=(255, 255, 255))
            
        except Exception as e:
            logger.error(f"Failed to add slide number: {e}")
    
    def _add_branding(self, draw: ImageDraw.Draw, width: int, height: int) -> None:
        """Add branding/watermark to image
        
        Args:
            draw: PIL ImageDraw object
            width: Image width
            height: Image height
        """
        try:
            # Simple text watermark (could be replaced with logo)
            brand_text = "Impact Consulting"
            font_size = min(width, height) // 60
            brand_font = self._get_font(font_size)
            
            # Position in bottom left
            bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = 20
            y = height - text_height - 20
            
            # Semi-transparent background
            padding = 3
            draw.rectangle(
                [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
                fill=(0, 0, 0, 100)
            )
            
            # Draw brand text
            draw.text((x, y), brand_text, font=brand_font, fill=(255, 255, 255, 180))
            
        except Exception as e:
            logger.error(f"Failed to add branding: {e}")
    
    def _get_font(self, size: int) -> ImageFont.ImageFont:
        """Get font for text rendering
        
        Args:
            size: Font size
            
        Returns:
            PIL ImageFont object
        """
        try:
            # Try to load a nice font (Arial, Helvetica, etc.)
            font_options = [
                "Arial.ttf",
                "arial.ttf", 
                "Helvetica.ttf",
                "helvetica.ttf",
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "/usr/share/fonts/truetype/arial.ttf",  # Linux
                "/Windows/Fonts/arial.ttf"  # Windows
            ]
            
            for font_path in font_options:
                try:
                    return ImageFont.truetype(font_path, size)
                except (OSError, IOError):
                    continue
            
            # Fallback to default font
            logger.warning("Could not load custom font, using default")
            return ImageFont.load_default()
            
        except Exception as e:
            logger.error(f"Error loading font: {e}")
            return ImageFont.load_default()
    
    def _get_lato_font(self, size: int) -> ImageFont.ImageFont:
        """Get Lato font for text rendering with fallback
        
        Args:
            size: Font size
            
        Returns:
            PIL ImageFont object
        """
        try:
            # Try to load Lato font first
            lato_options = [
                "Lato-Regular.ttf",
                "lato-regular.ttf",
                "/System/Library/Fonts/Lato-Regular.ttf",  # macOS
                "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",  # Linux
                "/Windows/Fonts/Lato-Regular.ttf"  # Windows
            ]
            
            for font_path in lato_options:
                try:
                    return ImageFont.truetype(font_path, size)
                except (OSError, IOError):
                    continue
            
            # Fallback to system fonts similar to Lato
            fallback_options = [
                "Arial.ttf",
                "arial.ttf", 
                "Helvetica.ttf",
                "helvetica.ttf",
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "/usr/share/fonts/truetype/arial.ttf",  # Linux
                "/Windows/Fonts/arial.ttf"  # Windows
            ]
            
            for font_path in fallback_options:
                try:
                    return ImageFont.truetype(font_path, size)
                except (OSError, IOError):
                    continue
            
            # Final fallback to default font
            logger.warning("Could not load Lato or similar font, using default")
            return ImageFont.load_default()
            
        except Exception as e:
            logger.error(f"Error loading Lato font: {e}")
            return ImageFont.load_default()
    
    def _wrap_text_to_lines(self, text: str, font: ImageFont.ImageFont, max_width: float, max_lines: int = 2) -> list[str]:
        """Wrap text to fit within specified width and line limit
        
        Args:
            text: Text to wrap
            font: Font to use for measuring
            max_width: Maximum width in pixels
            max_lines: Maximum number of lines
            
        Returns:
            List of wrapped text lines
        """
        try:
            words = text.split()
            if not words:
                return ['']
            
            lines = []
            current_line = []
            
            for word in words:
                # Test if adding this word would exceed width
                test_line = current_line + [word]
                test_text = ' '.join(test_line)
                
                # Use textlength for accurate measurement
                if hasattr(font, 'getlength'):
                    text_width = font.getlength(test_text)
                else:
                    # Fallback for older PIL versions
                    text_width = font.getsize(test_text)[0]
                
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    # Start new line if we haven't reached max lines
                    if len(lines) < max_lines - 1:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        # We're at max lines, truncate with ellipsis
                        if current_line:
                            lines.append(' '.join(current_line) + '...')
                        break
            
            # Add remaining words as final line
            if current_line and len(lines) < max_lines:
                lines.append(' '.join(current_line))
            
            return lines if lines else ['']
            
        except Exception as e:
            logger.error(f"Error wrapping text: {e}")
            return [text[:50] + '...' if len(text) > 50 else text]
    
    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: float) -> list[str]:
        """Wrap text to fit within specified width
        
        Args:
            text: Text to wrap
            font: Font to use for measuring
            max_width: Maximum width in pixels
            
        Returns:
            List of wrapped text lines
        """
        lines = []
        words = text.split()
        
        current_line = []
        for word in words:
            # Test adding this word to current line
            test_line = ' '.join(current_line + [word])
            
            # Create a temporary draw object for measuring
            temp_img = Image.new('RGB', (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            bbox = temp_draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]
            
            if line_width <= max_width:
                current_line.append(word)
            else:
                # Current line is full, start new line
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        # Add remaining words
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _wrap_text_optimized(self, text: str, font: ImageFont.ImageFont, box_width: int, max_lines: int = 3) -> list[str]:
        """Wrap text optimally for 2-3 lines with proper buffering
        
        Args:
            text: Text to wrap
            font: Font to use for measuring
            box_width: Total box width (90% of image width)
            max_lines: Maximum number of lines (default 3)
            
        Returns:
            List of wrapped text lines with optimal spacing
        """
        try:
            words = text.split()
            if not words:
                return ['']
            
            lines = []
            current_line = []
            
            # Use 80% of box width for text, leaving 10% buffer on each side
            usable_width = int(box_width * 0.8)
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                
                # Use textlength for accurate measurement
                if hasattr(font, 'getlength'):
                    text_width = font.getlength(test_line)
                else:
                    # Fallback for older PIL versions
                    text_width = font.getsize(test_line)[0]
                
                if text_width <= usable_width or not current_line:
                    current_line.append(word)
                else:
                    # Start new line if we haven't reached max lines
                    if len(lines) < max_lines - 1:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        # We're at max lines, finish current line
                        if current_line:
                            lines.append(' '.join(current_line))
                        break
            
            # Add remaining words as final line if within limit
            if current_line and len(lines) < max_lines:
                lines.append(' '.join(current_line))
            
            return lines if lines else [text]
            
        except Exception as e:
            logger.error(f"Error in optimized text wrapping: {e}")
            return [text[:50] + '...' if len(text) > 50 else text]