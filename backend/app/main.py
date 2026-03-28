import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import process
from app.routes import patients
from app.config import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Healthcare FHIR API",
    description="AI-powered clinical data extraction and FHIR bundle generation",
    version="1.0.0"
)


def _preload_paddleocr():
    """Load PaddleOCR models in background so first request is fast."""
    try:
        from app.services.ocr_strategies.image_based import PaddleOCREngine
        logger.info("Preloading PaddleOCR models (background thread)...")
        PaddleOCREngine.get_instance()
        logger.info("PaddleOCR models loaded — ready for requests")
    except Exception as e:
        logger.warning(f"PaddleOCR preload failed (will retry on first request): {e}")


@app.on_event("startup")
async def startup_event():
    """Start PaddleOCR preloading in background thread at app boot."""
    thread = threading.Thread(target=_preload_paddleocr, daemon=True)
    thread.start()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(process.router,  prefix="/api", tags=["process"])
app.include_router(patients.router, prefix="/api", tags=["patients"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Healthcare FHIR API",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
