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
    ) -> Tuple[bytes, Optional[str]]:
        """Create a carousel slide with text overlay and overflow detection
        
        Args:
            background_image_data: Background image as bytes
            text: Text to overlay
            is_title_slide: Whether this is a title slide
            slide_number: Slide number for non-title slides
            
        Returns:
            Tuple of (processed_image_bytes, overflow_text)
            
        Raises:
            ImageProcessingError: If image processing fails
        """
        try:
            logger.info(f"Creating carousel slide. Title slide: {is_title_slide}")
            
            # Load background image
            background = Image.open(BytesIO(background_image_data))
            
            # Ensure background matches expected dimensions
            if background.size != (self.width, self.height):
                # Only resize if dimensions don't match to maintain 1:1 ratio
                background = background.resize((self.width, self.height), Image.Resampling.LANCZOS)
                logger.debug(f"Resized background from {background.size} to {self.width}x{self.height}")
            
            # Ensure RGB mode
            if background.mode != 'RGB':
                background = background.convert('RGB')
            
            # Create drawing context
            draw = ImageDraw.Draw(background)
            
            # Re-enable text rendering with improved contrast and sizing
            # Text rendered separately over clean aesthetic background
            overflow_text = None
            if is_title_slide:
                overflow_text = self._add_title_text(draw, text, self.width, self.height)
            else:
                overflow_text = self._add_content_text(draw, text, self.width, self.height, slide_number)
            
            # Branding removed per user request
            # self._add_branding(draw, self.width, self.height)
            
            # Convert to bytes
            output_buffer = BytesIO()
            background.save(output_buffer, format='PNG', optimize=True)
            
            return output_buffer.getvalue(), overflow_text
            
        except Exception as e:
            error_msg = f"Failed to create carousel slide: {e}"
            logger.error(error_msg)
            raise ImageProcessingError(error_msg)
    
    def _add_title_text(self, draw: ImageDraw.Draw, title: str, width: int, height: int) -> Optional[str]:
        """Add title text to image with intelligent font sizing
        
        Args:
            draw: PIL ImageDraw object
            title: Title text
            width: Image width
            height: Image height
        """
        try:
            # Start with larger font and scale down if needed
            optimal_font_size = self._calculate_optimal_title_font_size(title, width, height)
            title_font = self._get_lato_font(optimal_font_size)
            
            # Calculate text dimensions first
            bbox = draw.textbbox((0, 0), title, font=title_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Center text position
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            # Create semi-opaque background box
            padding = 40
            box_left = x - padding
            box_top = y - padding  
            box_right = x + text_width + padding
            box_bottom = y + text_height + padding
            
            # Draw semi-opaque background
            background_image = draw._image
            background_rgba = background_image.convert('RGBA')
            box_overlay = Image.new('RGBA', background_rgba.size, (0, 0, 0, 0))
            box_draw = ImageDraw.Draw(box_overlay)
            box_draw.rounded_rectangle(
                [box_left, box_top, box_right, box_bottom],
                radius=20,
                fill=(255, 255, 255, 153)  # White with 60% opacity
            )
            
            # Composite the box overlay onto the main image
            background_rgba = Image.alpha_composite(background_rgba, box_overlay)
            final_image = background_rgba.convert('RGB')
            draw._image.paste(final_image)
            
            # Create new draw context and draw text
            final_draw = ImageDraw.Draw(draw._image)
            text_color = (64, 64, 64)  # Dark gray
            
            final_draw.text(
                (x, y), 
                title, 
                font=title_font, 
                fill=text_color,
                anchor="lt"
            )
            
            logger.debug(f"Added title text at position ({x}, {y})")
            return None  # Titles typically don't overflow
            
        except Exception as e:
            logger.error(f"Failed to add title text: {e}")
            return None
    
    def _add_content_text(
        self, 
        draw: ImageDraw.Draw, 
        content: str, 
        width: int, 
        height: int,
        slide_number: Optional[int] = None
    ) -> Optional[str]:
        """Add content text to image with semi-opaque white box
        
        Args:
            draw: PIL ImageDraw object
            content: Content text
            width: Image width
            height: Image height
            slide_number: Slide number
        """
        try:
            # Use intelligent font sizing with 60pt minimum for maximum legibility
            optimal_font_size = self._calculate_optimal_content_font_size(content, width, height)
            content_font = self._get_lato_font(optimal_font_size)
            
            # Text box width should be 90% of total image width
            text_box_width = int(width * 0.9)  # 90% of image width
            text_box_left_margin = int(width * 0.05)  # 5% margin on each side
            
            # Split content with overflow intelligence - prioritize readability over content density
            lines, overflow_text = self._wrap_text_with_overflow_intelligence(content, content_font, text_box_width, max_lines=3)
            
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
            
            # Convert back to RGB and create new draw context for text rendering
            final_image = background_rgba.convert('RGB')
            
            # Replace the original image with the composited version
            draw._image.paste(final_image)
            
            # Create a new draw context on the final composited image
            final_draw = ImageDraw.Draw(draw._image)
            
            # Choose dark text color that complements real estate theme
            text_color = (64, 64, 64)  # Dark gray - readable and warm
            
            # Draw text lines with proper positioning within the 90% width box
            text_y = box_y + box_padding
            for line in lines:
                # Center each line within the 90% width box
                line_width = final_draw.textlength(line, font=content_font)
                text_x = text_box_left_margin + (text_box_width - line_width) // 2
                
                final_draw.text(
                    (text_x, text_y),
                    line,
                    font=content_font,
                    fill=text_color
                )
                text_y += line_height
            
            # Add slide number if provided (using the new draw context)
            if slide_number is not None:
                self._add_slide_number(final_draw, slide_number, width, height)
            
            # Log overflow handling for debugging
            if overflow_text:
                logger.info(f"Content overflow detected: '{overflow_text}' - should create additional slide")
            
            logger.debug(f"Added content text with {len(lines)} lines at {optimal_font_size}pt font size")
            return overflow_text
            
        except Exception as e:
            logger.error(f"Failed to add content text: {e}")
            return None
    
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
                "/System/Library/Fonts/Helvetica.ttc",  # macOS - move most likely to succeed first
                "/System/Library/Fonts/HelveticaNeue.ttc",  # macOS alternative
                "Arial.ttf",
                "arial.ttf", 
                "Helvetica.ttf",
                "helvetica.ttf",
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/usr/share/fonts/truetype/arial.ttf",  # Linux
                "/Windows/Fonts/arial.ttf"  # Windows
            ]
            
            for font_path in font_options:
                try:
                    font = ImageFont.truetype(font_path, size)
                    logger.debug(f"Successfully loaded font: {font_path} at {size}pt")
                    return font
                except (OSError, IOError):
                    continue
            
            # Fallback to default font - but warn about potential size issues
            logger.warning(f"Could not load any TrueType font, using PIL default. Font size {size}pt may not render correctly.")
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
                    font = ImageFont.truetype(font_path, size)
                    logger.info(f"Successfully loaded Lato font: {font_path} at {size}pt")
                    return font
                except (OSError, IOError):
                    continue
            
            # Fallback to system fonts similar to Lato
            fallback_options = [
                "/System/Library/Fonts/Helvetica.ttc",  # macOS - move most likely to succeed first
                "/System/Library/Fonts/HelveticaNeue.ttc",  # macOS alternative
                "Arial.ttf",
                "arial.ttf", 
                "Helvetica.ttf",
                "helvetica.ttf",
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/usr/share/fonts/truetype/arial.ttf",  # Linux
                "/Windows/Fonts/arial.ttf"  # Windows
            ]
            
            for font_path in fallback_options:
                try:
                    font = ImageFont.truetype(font_path, size)
                    logger.info(f"Successfully loaded fallback font: {font_path} at {size}pt")
                    return font
                except (OSError, IOError):
                    continue
            
            # Final fallback to default font - but warn about potential size issues
            logger.warning(f"Could not load any TrueType font, using PIL default. Font size {size}pt may not render correctly.")
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
    
    def _calculate_optimal_title_font_size(self, title: str, width: int, height: int) -> int:
        """Calculate optimal font size for title text with minimum 60pt
        
        Args:
            title: Title text
            width: Image width
            height: Image height
            
        Returns:
            Optimal font size (minimum 60pt for maximum impact)
        """
        try:
            # Use config values for font sizing
            min_font_size = config.min_title_font_size
            max_font_size = config.max_title_font_size
            
            # Available text area (80% width, 40% height for titles)
            available_width = int(width * 0.8)
            available_height = int(height * 0.4)
            
            # Try font sizes from max to min
            for font_size in range(max_font_size, min_font_size - 1, -4):
                test_font = self._get_lato_font(font_size)
                
                # Test if title fits in single line with this font size
                if hasattr(test_font, 'getlength'):
                    text_width = test_font.getlength(title)
                    metrics = test_font.getmetrics()
                    text_height = metrics[0] + metrics[1]  # ascent + descent
                else:
                    # Fallback for older PIL
                    text_width, text_height = test_font.getsize(title)
                
                # Check if text fits with padding
                padding = 40
                if (text_width + padding * 2) <= available_width and (text_height + padding * 2) <= available_height:
                    logger.info(f"Optimal title font size: {font_size}pt for '{title[:30]}...'")
                    return font_size
            
            # Use minimum font size if nothing fits
            logger.warning(f"Using minimum title font size {min_font_size}pt - text may be tight")
            return min_font_size
            
        except Exception as e:
            logger.error(f"Error calculating title font size: {e}")
            return 60  # Safe fallback
    
    def _calculate_optimal_content_font_size(self, content: str, width: int, height: int) -> int:
        """Calculate optimal font size for content text with minimum 60pt
        
        Args:
            content: Content text
            width: Image width  
            height: Image height
            
        Returns:
            Optimal font size (minimum 60pt for maximum legibility)
        """
        try:
            # Use config values for font sizing
            min_font_size = config.min_content_font_size
            max_font_size = config.max_content_font_size
            
            # Available text area (90% width, 60% height for content)
            text_box_width = int(width * 0.9)
            available_height = int(height * 0.6)
            
            # Try font sizes from max to min
            for font_size in range(max_font_size, min_font_size - 1, -4):
                test_font = self._get_lato_font(font_size)
                
                # Test text wrapping with this font size
                lines, overflow = self._wrap_text_with_overflow_intelligence(content, test_font, text_box_width, max_lines=3)
                
                # Calculate total height needed
                if hasattr(test_font, 'getmetrics'):
                    metrics = test_font.getmetrics()
                    line_height = int((metrics[0] + metrics[1]) * 1.4)  # Line spacing
                else:
                    # Fallback
                    line_height = int(font_size * 1.4)
                
                total_text_height = len(lines) * line_height
                padding = int(width * 0.06)  # 6% padding
                
                # Check if text fits without overflow and within height
                if not overflow and (total_text_height + padding * 2) <= available_height:
                    logger.info(f"Optimal content font size: {font_size}pt for content length {len(content)}")
                    return font_size
            
            # Use minimum font size if nothing fits
            logger.warning(f"Using minimum content font size {min_font_size}pt - may need overflow handling")
            return min_font_size
            
        except Exception as e:
            logger.error(f"Error calculating content font size: {e}")
            return 60  # Safe fallback
    
    def _wrap_text_with_overflow_intelligence(self, text: str, font: ImageFont.ImageFont, box_width: int, max_lines: int = 3) -> tuple[list[str], str]:
        """Wrap text with overflow intelligence - returns text that fits and overflow text
        
        Args:
            text: Text to wrap
            font: Font to use for measuring
            box_width: Total box width (90% of image width)
            max_lines: Maximum number of lines (default 3)
            
        Returns:
            Tuple of (lines_that_fit, overflow_text)
        """
        try:
            words = text.split()
            if not words:
                return [''], ''
            
            lines = []
            current_line = []
            overflow_words = []
            
            # Use 80% of box width for text, leaving 10% buffer on each side
            usable_width = int(box_width * 0.8)
            
            for i, word in enumerate(words):
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
                        # We're at max lines - everything else is overflow
                        if current_line:
                            lines.append(' '.join(current_line))
                        overflow_words = words[i:]
                        break
            
            # Add remaining words as final line if within limit and no overflow
            if current_line and len(lines) < max_lines and not overflow_words:
                lines.append(' '.join(current_line))
            elif current_line and not overflow_words:
                # If we have remaining words but reached max lines, they become overflow
                overflow_words = current_line
            
            overflow_text = ' '.join(overflow_words) if overflow_words else ''
            
            return lines if lines else [text], overflow_text
            
        except Exception as e:
            logger.error(f"Error in overflow-intelligent text wrapping: {e}")
            return [text[:50] + '...' if len(text) > 50 else text], ''