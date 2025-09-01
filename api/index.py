"""
Production Vercel entry point for Carousel Engine v2
All diagnostic tests passed - deploying full application
"""

# Import the full carousel engine application
from carousel_engine.api.main import app

# Export the FastAPI app for Vercel
# This now includes all routes: health, carousel generation, document upload, webhooks