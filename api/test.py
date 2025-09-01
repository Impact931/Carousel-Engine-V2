"""
Minimal test deployment for Vercel debugging
"""

from fastapi import FastAPI

# Create minimal FastAPI app for testing
app = FastAPI(title="Test App")

@app.get("/")
def root():
    return {"message": "Minimal test app working", "status": "success"}

@app.get("/health")  
def health():
    return {"status": "healthy", "test": True}

# Export for Vercel
handler = app