import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import process
from app.routes import patients
from app.routes import pre_auth
from app.routes import enhancements
from app.routes import discharge
from app.routes import settlement
from app.routes import cases
from app.routes import config
from app.routes import mis
from app.routes import financial_audit
from app.routes import bank_statement
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
    """Load doctr OCR models in background so first request is fast."""
    try:
        from app.services.ocr_strategies.image_based import PaddleOCREngine
        logger.info("Preloading doctr OCR models (background thread)...")
        PaddleOCREngine.get_instance()
        logger.info("doctr OCR models loaded — ready for requests")
    except Exception as e:
        logger.warning(f"doctr preload failed (will retry on first request): {e}")


@app.on_event("startup")
async def startup_event():
    """Start PaddleOCR preloading in background thread at app boot.
    Set DISABLE_OCR_PRELOAD=true to skip on memory-constrained deployments.
    """
    import os
    if os.getenv("DISABLE_OCR_PRELOAD", "false").lower() == "true":
        logger.info("OCR preload skipped (DISABLE_OCR_PRELOAD=true)")
        return
    thread = threading.Thread(target=_preload_paddleocr, daemon=True)
    thread.start()

# Configure CORS — FRONTEND_URL supports comma-separated values for multiple origins
import os as _os
_allowed_origins = ["http://localhost:5173", "http://localhost:3000"]
for _url in settings.FRONTEND_URL.split(","):
    _url = _url.strip()
    if _url and _url not in _allowed_origins:
        _allowed_origins.append(_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(process.router,   prefix="/api", tags=["process"])
app.include_router(patients.router,  prefix="/api", tags=["patients"])
app.include_router(pre_auth.router,       prefix="/api", tags=["pre-auth"])
app.include_router(enhancements.router,   prefix="/api", tags=["enhancements"])
app.include_router(discharge.router,      prefix="/api", tags=["discharge"])
app.include_router(settlement.router,     prefix="/api", tags=["settlement"])
app.include_router(cases.router,          prefix="/api", tags=["cases"])
app.include_router(config.router,         prefix="/api", tags=["config"])
app.include_router(mis.router,            prefix="/api", tags=["mis"])
app.include_router(financial_audit.router,  prefix="/api", tags=["financial-audit"])
app.include_router(bank_statement.router,  prefix="/api", tags=["bank-statement"])

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
