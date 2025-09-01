"""
Vercel entry point for Carousel Engine v2
"""

# For Vercel, we need to import the FastAPI app directly
try:
    from carousel_engine.api.main import app
    # Export the app for Vercel to find
    # Vercel looks for 'app' or 'handler' variable
    handler = app
except ImportError as e:
    # Fallback minimal app if import fails
    from fastapi import FastAPI
    handler = FastAPI()
    
    @handler.get("/")
    def root():
        return {"error": "Import failed", "details": str(e)}
    
    @handler.get("/health")
    def health():
        return {"status": "error", "message": f"Failed to import main app: {e}"}