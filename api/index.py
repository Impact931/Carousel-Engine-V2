"""
Vercel-compatible entry point with gradual carousel engine integration
"""

from fastapi import FastAPI

# Test 1: Basic FastAPI (WORKING)
app = FastAPI(title="Carousel Engine v2", description="Production deployment")

@app.get("/")
def read_root():
    return {"message": "Carousel Engine v2 - Basic FastAPI working", "status": "success"}

@app.get("/health")
def basic_health():
    return {"status": "healthy", "framework": "FastAPI", "test": "basic"}

# Test 2: Try importing carousel engine configuration
@app.get("/config-test")
def config_test():
    try:
        from carousel_engine.core.config import config
        return {
            "status": "success", 
            "message": "Config imported successfully",
            "app_name": config.app_name,
            "version": config.version
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Config import failed: {str(e)}",
            "type": type(e).__name__
        }

# Test 3: Try importing the main app but don't initialize services
@app.get("/import-test")
def import_test():
    try:
        # Just test if we can import without initializing
        import carousel_engine.api.main as main_module
        return {
            "status": "success",
            "message": "Main module imported successfully",
            "module": str(type(main_module))
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Main module import failed: {str(e)}",
            "type": type(e).__name__
        }