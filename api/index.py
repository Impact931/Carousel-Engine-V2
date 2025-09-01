"""
Vercel-compatible entry point following current documentation
"""

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Working with modern Vercel Python setup"}

@app.get("/api/health")
def health():
    return {"status": "healthy", "framework": "FastAPI"}

# For Vercel, export the FastAPI app directly
# Vercel's @vercel/python runtime looks for 'app' variable