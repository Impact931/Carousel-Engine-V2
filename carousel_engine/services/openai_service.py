"""
OpenAI API service for Carousel Engine v2
"""

import logging
from typing import Optional
import openai
from openai import OpenAI
import requests

from ..core.config import config
from ..core.exceptions import OpenAIError

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for interacting with OpenAI API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI service
        
        Args:
            api_key: OpenAI API key, defaults to config value
        """
        self.client = OpenAI(api_key=api_key or config.openai_api_key)
        self.total_cost = 0.0
        
    async def generate_background_description(
        self, 
        title: str, 
        style: str = "professional social media background",
        theme: str = "modern"
    ) -> tuple[str, float]:
        """Generate a background image description using GPT model
        
        Args:
            title: Content title for image context
            style: Image style description
            theme: Visual theme (luxury, modern, warm, professional, vibrant)
            
        Returns:
            Tuple of (background_description, estimated_cost)
            
        Raises:
            OpenAIError: If description generation fails
        """
        try:
            logger.info(f"Generating background description for title: {title}")
            
            # Create prompt for background description
            prompt = self._create_background_description_prompt(title, style, theme)
            
            # Check cost limit
            estimated_cost = self._estimate_gpt_cost(prompt)
            if self.total_cost + estimated_cost > config.max_cost_per_run:
                raise OpenAIError(
                    f"Cost limit would be exceeded. Current: ${self.total_cost:.2f}, "
                    f"Estimated: ${estimated_cost:.2f}, Limit: ${config.max_cost_per_run:.2f}",
                    prompt=prompt
                )
            
            # Generate background description
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional graphic designer specializing in social media background designs."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            background_description = response.choices[0].message.content.strip()
            
            # Calculate actual cost
            actual_cost = self._calculate_actual_gpt_cost(response.usage)
            self.total_cost += actual_cost
            
            logger.info(f"Successfully generated background description. Cost: ${actual_cost:.4f}")
            return background_description, actual_cost
            
        except openai.OpenAIError as e:
            error_msg = f"OpenAI API error generating background description: {e}"
            logger.error(error_msg)
            raise OpenAIError(error_msg, prompt=prompt)
        except Exception as e:
            error_msg = f"Unexpected error generating background description: {e}"
            logger.error(error_msg)
            raise OpenAIError(error_msg, prompt=prompt)
    
    async def optimize_content_for_slides(
        self, 
        content: str, 
        max_slides: int = 5,
        lines_per_slide: int = 2,
        client_system_message: Optional[str] = None
    ) -> tuple[list[str], float]:
        """Optimize content for carousel slides using GPT
        
        Args:
            content: Raw content text
            max_slides: Maximum number of content slides (excluding title)
            lines_per_slide: Maximum lines per slide
            client_system_message: Optional client-specific system message for personalization
            
        Returns:
            Tuple of (optimized_slide_texts, estimated_cost)
            
        Raises:
            OpenAIError: If content optimization fails
        """
        try:
            logger.info(f"Optimizing content for {max_slides} slides")
            
            # Create system message - personalize if client system message available
            system_message = "You are an expert social media content creator who specializes in creating engaging carousel posts."
            if client_system_message:
                system_message += f"\n\nClient-specific instructions and context:\n{client_system_message}"
                logger.info("Using personalized system message with client context")
            
            # Create prompt for content optimization
            prompt = self._create_content_optimization_prompt(content, max_slides, lines_per_slide)
            
            # Estimate cost
            estimated_cost = self._estimate_gpt_cost(prompt)
            if self.total_cost + estimated_cost > config.max_cost_per_run:
                raise OpenAIError(
                    f"Cost limit would be exceeded. Current: ${self.total_cost:.2f}, "
                    f"Estimated: ${estimated_cost:.2f}, Limit: ${config.max_cost_per_run:.2f}",
                    prompt=prompt
                )
            
            # Call GPT-5
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            # Parse response
            content_text = response.choices[0].message.content
            slide_texts = self._parse_optimized_content(content_text)
            
            # Update cost tracking
            actual_cost = self._calculate_actual_gpt_cost(response.usage)
            self.total_cost += actual_cost
            
            logger.info(f"Successfully optimized content into {len(slide_texts)} slides. Cost: ${actual_cost:.4f}")
            return slide_texts, actual_cost
            
        except openai.OpenAIError as e:
            error_msg = f"OpenAI API error optimizing content: {e}"
            logger.error(error_msg)
            raise OpenAIError(error_msg, prompt=prompt)
        except Exception as e:
            error_msg = f"Unexpected error optimizing content: {e}"
            logger.error(error_msg)
            raise OpenAIError(error_msg, prompt=prompt)

    async def generate_text_completion(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3
    ) -> str:
        """Generate text completion using GPT
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Creativity level (0.0-1.0)
            
        Returns:
            Generated text response
            
        Raises:
            OpenAIError: If text generation fails
        """
        try:
            logger.info(f"Generating text completion: {len(prompt)} chars prompt")
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if not response or not response.choices:
                raise OpenAIError("No response from OpenAI API")
            
            content = response.choices[0].message.content
            if not content:
                raise OpenAIError("Empty response from OpenAI API")
            
            # Track costs
            cost = self._calculate_actual_gpt_cost(response.usage)
            self.total_cost += cost
            
            logger.info(f"Generated text completion: {len(content)} chars, cost: ${cost:.4f}")
            return content
            
        except openai.OpenAIError as e:
            error_msg = f"OpenAI API error generating text: {e}"
            logger.error(error_msg)
            raise OpenAIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error generating text: {e}"
            logger.error(error_msg)
            raise OpenAIError(error_msg)
    
    def get_total_cost(self) -> float:
        """Get total cost for this service instance
        
        Returns:
            Total cost in USD
        """
        return self.total_cost
    
    def reset_cost_tracking(self) -> None:
        """Reset cost tracking to zero"""
        self.total_cost = 0.0
    
    def _create_background_description_prompt(self, title: str, style: str, theme: str) -> str:
        """Create prompt for generating background image description based on content
        
        Args:
            title: Content title
            style: Image style description
            theme: Visual theme (luxury, modern, warm, professional, vibrant)
            
        Returns:
            Prompt for generating detailed background description
        """
        # Extract key themes from title for content-specific imagery
        title_lower = title.lower()
        content_themes = []
        
        # Theme-specific visual elements
        if any(word in title_lower for word in ['peace', 'confidence', 'mind', 'secure']):
            content_themes.extend(['serene bedroom with soft pillows', 'quiet reading nook', 'peaceful family room'])
        elif any(word in title_lower for word in ['budget', 'cost', 'money', 'financial']):
            content_themes.extend(['organized home office', 'clean kitchen with calculators', 'tidy financial planning space'])
        elif any(word in title_lower for word in ['lifestyle', 'living', 'community', 'neighborhood']):
            content_themes.extend(['vibrant living room with community views', 'welcoming front porch', 'family gathering space'])
        elif any(word in title_lower for word in ['upgrade', 'improve', 'better', 'enhance']):
            content_themes.extend(['modern renovated kitchen', 'stylish updated bathroom', 'contemporary living space'])
        elif any(word in title_lower for word in ['slow', 'pause', 'patient', 'careful']):
            content_themes.extend(['quiet meditation corner', 'calm study space', 'peaceful contemplation area'])
        else:
            # Default themes
            content_themes.extend(['welcoming living room', 'bright kitchen area', 'cozy family space'])
        
        # Select a theme
        import random
        selected_theme = random.choice(content_themes)
        
        # Theme style mappings
        theme_styles = {
            "luxury": "luxurious materials, marble textures, gold accents, premium finishes, sophisticated lighting",
            "modern": "clean lines, minimalist design, contemporary furniture, geometric shapes, neutral colors",
            "warm": "warm colors, cozy atmosphere, inviting textures, soft lighting, comfortable furnishings",
            "professional": "clean and organized, sophisticated neutral colors, business-appropriate aesthetics",
            "vibrant": "bright accent colors, energetic atmosphere, dynamic composition, bold design elements"
        }
        
        theme_description = theme_styles.get(theme, theme_styles["modern"])
        
        return (
            f"Create a detailed description for a {theme} social media background image for real estate content titled: '{title}'. "
            f"The background should feature: {selected_theme} with {theme_description}. "
            f"Style requirements: {style} with excellent contrast areas for text overlay. "
            f"The image should evoke emotions related to the theme of '{title}' while maintaining professional real estate standards. "
            f"Avoid: people, text, logos, busy patterns, or overly detailed elements that would interfere with text readability. "
            f"Focus on: architectural elements, interior design, lighting, and spatial composition that supports the emotional message of '{title}'. "
            f"Describe the color palette, lighting conditions, furniture arrangement, and any unique design elements that make this background "
            f"specifically tailored to the content theme. Keep the description detailed but concise (under 200 words)."
        )
    
    def _create_content_optimization_prompt(
        self, 
        content: str, 
        max_slides: int, 
        lines_per_slide: int
    ) -> str:
        """Create prompt for content optimization
        
        Args:
            content: Raw content
            max_slides: Maximum slides
            lines_per_slide: Lines per slide
            
        Returns:
            Content optimization prompt
        """
        return (
            f"You are GPT-5, enhanced with 20 years of proven social media marketing expertise. You are a MASTER "
            f"social media content creator with demonstrated success creating viral, engagement-driving content that "
            f"generates leads and builds deep audience connections. You understand exactly what makes people stop "
            f"scrolling, engage emotionally, and take action.\n\n"
            
            f"Your enhanced expertise includes:\n"
            f"- Psychology of social media engagement and human behavior\n"
            f"- Creating content that builds trust and drives conversions\n"
            f"- Crafting connected narratives that flow seamlessly from slide to slide\n"
            f"- Understanding real estate buyer psychology and emotional triggers\n"
            f"- Building anticipation and maintaining engagement throughout entire carousels\n"
            f"- 20 years of real-world social media marketing success\n\n"
            
            f"Transform the following real estate content into 4-7 compelling carousel slides that tell a CONNECTED STORY. "
            f"Each slide must have EXACTLY {lines_per_slide} lines maximum - NO MORE.\n\n"
            
            f"FORMAT EXAMPLE (each slide must look EXACTLY like this):\n"
            f"SLIDE 1:\n"
            f"Most agents hand you keys and disappear.\n"
            f"But what about your peace of mind?\n\n"
            
            f"SLIDE 2:\n" 
            f"Here's what we learned after 500+ closings...\n"
            f"The real upgrade isn't the house.\n\n"
            
            f"CRITICAL FORMAT RULES:\n"
            f"- Each slide = EXACTLY {lines_per_slide} lines\n"
            f"- Each line = One complete sentence or thought\n"
            f"- NO bullet points, NO sub-points, NO extra text\n"
            f"- If you write more than {lines_per_slide} lines, the system will REJECT your content\n\n"
            
            f"CRITICAL: The slides must flow together as one cohesive narrative. Each slide should:\n"
            f"- Build upon the previous slide's message\n"
            f"- Create natural curiosity for the next slide\n"
            f"- Use connecting phrases and transitions\n"
            f"- Feel like chapters in the same story, not random standalone statements\n"
            f"- NEVER exceed {lines_per_slide} lines per slide\n\n"
            
            f"Choose the most engaging narrative structure:\n"
            f"- Problem → Agitation → Solution story arc with emotional journey\n"
            f"- Step-by-step revelation building to a powerful conclusion\n"
            f"- Contrarian truth that challenges assumptions and provides breakthrough insight\n"
            f"- Behind-the-scenes story that reveals insider knowledge\n\n"
            
            f"Writing style requirements:\n"
            f"- NO title slide - jump straight into a compelling hook\n"
            f"- Use conversational, authentic language that builds trust\n"
            f"- Include emotional triggers that resonate with home buyers/sellers\n"
            f"- Create 'scroll-stopping' moments with unexpected insights\n"
            f"- End with a powerful statement that drives engagement/comments\n"
            f"- Make each slide feel essential to understanding the complete message\n\n"
            
            f"CRITICAL FORMATTING REQUIREMENTS:\n"
            f"- Do NOT include any introductory text, explanations, or commentary\n"
            f"- Do NOT include phrases like 'Here's your carousel', 'I'll create', or 'Let me craft'\n"
            f"- Do NOT include any meta-commentary about the content\n"
            f"- Start immediately with 'SLIDE 1:' followed by the actual slide content\n"
            f"- Each slide should contain ONLY the text that will appear on the slide\n"
            f"- No preparatory statements, conclusions, or additional context\n\n"
            f"Format your response EXACTLY as:\n"
            f"SLIDE 1:\n[actual slide text only]\n\n"
            f"SLIDE 2:\n[actual slide text only]\n\n"
            f"... and so on\n\n"
            f"Content to transform:\n{content}"
        )
    
    def _parse_optimized_content(self, content_text: str) -> list[str]:
        """Parse GPT response into slide texts, filtering out unwanted content
        
        Args:
            content_text: GPT response text
            
        Returns:
            List of clean slide texts
        """
        slides = []
        current_slide = []
        
        # Filter out common unwanted phrases
        unwanted_phrases = [
            "here's your carousel",
            "i'll create",
            "let me craft",
            "here are the slides",
            "i've created",
            "this carousel",
            "here's how",
            "let's break this down",
            "i've optimized",
            "here's the content",
            "based on your request"
        ]
        
        lines = content_text.split('\n')
        for line in lines:
            line = line.strip()
            
            if line.startswith('SLIDE '):
                # Save previous slide
                if current_slide:
                    slide_text = '\n'.join(current_slide).strip()
                    if slide_text:  # Only add non-empty slides
                        slides.append(slide_text)
                    current_slide = []
            elif line and not line.startswith('SLIDE '):
                # Check if this line contains unwanted phrases
                line_lower = line.lower()
                contains_unwanted = any(phrase in line_lower for phrase in unwanted_phrases)
                
                # Skip lines that are clearly commentary/meta-text
                if not contains_unwanted and not line.startswith('*') and not line.startswith('[') and not line.startswith('Note:'):
                    current_slide.append(line)
        
        # Save last slide
        if current_slide:
            slide_text = '\n'.join(current_slide).strip()
            if slide_text:  # Only add non-empty slides
                slides.append(slide_text)
        
        return slides
    
    def _estimate_dalle_cost(self, size: str) -> float:
        """Estimate DALL-E API cost
        
        Args:
            size: Image size
            
        Returns:
            Estimated cost in USD
        """
        # DALL-E 3 pricing (as of 2024)
        if size == "1024x1024":
            return 0.040  # $0.040 per image
        elif size in ["1792x1024", "1024x1792"]:
            return 0.080  # $0.080 per image
        else:
            return 0.040  # Default to standard pricing
    
    def _estimate_gpt_cost(self, prompt: str) -> float:
        """Estimate GPT-5 API cost
        
        Args:
            prompt: Input prompt
            
        Returns:
            Estimated cost in USD
        """
        # Rough token estimation (4 chars ≈ 1 token)
        input_tokens = len(prompt) // 4
        output_tokens = 500  # Estimated output
        
        # GPT-5 pricing (as of 2024)
        input_cost = input_tokens * 0.00003  # $0.03 per 1K tokens
        output_cost = output_tokens * 0.00006  # $0.06 per 1K tokens
        
        return input_cost + output_cost
    
    def _calculate_actual_gpt_cost(self, usage) -> float:
        """Calculate actual GPT cost from usage
        
        Args:
            usage: OpenAI usage object
            
        Returns:
            Actual cost in USD
        """
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        
        # GPT-5 pricing
        input_cost = input_tokens * 0.00003  # $0.03 per 1K tokens
        output_cost = output_tokens * 0.00006  # $0.06 per 1K tokens
        
        return input_cost + output_cost