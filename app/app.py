"""
FastAPI application for PDF rendering service.

Provides REST API endpoints for document rendering with error handling,
logging, and health checks.

License: MIT
"""

import time
import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.models import Document
from app.renderer import render_document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Study Note PDF Generator API",
    version="1.0.0",
    description="Production-ready API for generating beautifully formatted study-note style PDFs",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing information."""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} "
        f"completed in {duration:.3f}s with status {response.status_code}"
    )
    
    return response


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Status dictionary indicating service health
    """
    return {"status": "ok"}


@app.post("/render")
async def render_pdf(document: Document) -> Response:
    """
    Render a document to PDF.
    
    Args:
        document: Document structure with metadata and content blocks
        
    Returns:
        PDF file as binary response
        
    Raises:
        HTTPException: On validation or rendering errors
    """
    try:
        start_time = time.time()
        
        # Render document
        pdf_bytes = render_document(document)
        
        render_time = time.time() - start_time
        logger.info(f"Rendered document with {len(document.blocks)} blocks in {render_time:.3f}s")
        
        # Return PDF
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{document.meta.title or "document"}.pdf"',
                "X-Render-Time": f"{render_time:.3f}"
            }
        )
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Rendering error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rendering error: {str(e)}")


@app.exception_handler(413)
async def payload_too_large_handler(request: Request, exc: Any):
    """Handle payload too large errors."""
    return JSONResponse(
        status_code=413,
        content={"error": "Payload too large", "detail": "Request body exceeds maximum size"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
