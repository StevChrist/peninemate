from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import logging

from .routes import router
from .middleware import setup_middleware, setup_exception_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="PenineMate API",
    description="Intelligent Movie Q&A System - REST API for answering questions about movies",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup middleware and exception handlers
setup_middleware(app)
setup_exception_handlers(app)

# Include routes
app.include_router(router)

@app.get("/")
async def root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/docs")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting PenineMate API...")
    logger.info("API Documentation available at: http://localhost:8000/docs")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down PenineMate API...")
