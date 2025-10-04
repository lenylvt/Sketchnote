"""
FastAPI application for PDF rendering service.

Provides REST API endpoints for document rendering with error handling,
logging, and health checks.

License: MIT
"""

import time
import logging
import base64
import uuid
import os
import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Body
from fastapi.responses import Response, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.models import Document
from app.renderer import render_document
from app.auto_repair import AutoRepair, create_repair_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create temp directory for PDFs
TEMP_DIR = Path("/tmp/sketchnote-pdfs")
TEMP_DIR.mkdir(exist_ok=True)
MAX_PDF_AGE = 3600  # 1 hour


def cleanup_old_pdfs():
    """Delete PDFs older than 1 hour."""
    now = time.time()
    deleted_count = 0
    
    for pdf_file in TEMP_DIR.glob("*.pdf"):
        try:
            if now - pdf_file.stat().st_mtime > MAX_PDF_AGE:
                pdf_file.unlink()
                deleted_count += 1
        except Exception as e:
            logger.error(f"Cleanup error for {pdf_file.name}: {e}")
    
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old PDF(s)")


async def periodic_cleanup():
    """Run cleanup every 30 minutes."""
    while True:
        await asyncio.sleep(1800)  # 30 minutes
        cleanup_old_pdfs()

# Create FastAPI app
app = FastAPI(
    title="Study Note PDF Generator API",
    version="1.0.0",
    description="Production-ready API for generating beautifully formatted study-note style PDFs",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Mount temp directory for serving PDFs
app.mount("/temp-pdfs", StaticFiles(directory=str(TEMP_DIR)), name="temp_pdfs")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Start background cleanup task."""
    asyncio.create_task(periodic_cleanup())
    logger.info("Started periodic PDF cleanup task")


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
async def render_pdf(request: Request, raw_body: str = Body(..., media_type="application/json")) -> Response:
    """
    Render a document to PDF with auto-repair for malformed JSON.
    
    Args:
        request: FastAPI request object
        raw_body: Raw request body (for auto-repair)
        
    Returns:
        PDF file as binary response
        
    Raises:
        HTTPException: On validation or rendering errors
    """
    repairs_applied = []
    
    try:
        start_time = time.time()
        
        # Try to parse and repair JSON
        success, repaired_json, error = AutoRepair.repair_json(raw_body)
        if not success:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {error}")
        
        if repaired_json != raw_body:
            repairs_applied.append("JSON auto-repaired")
        
        # Parse JSON
        data = json.loads(repaired_json)
        
        # Repair document structure
        success, data, structure_repairs = AutoRepair.repair_document_structure(data)
        repairs_applied.extend(structure_repairs)
        
        # Try to validate with Pydantic
        try:
            document = Document(**data)
        except ValidationError as ve:
            # Attempt auto-fix
            logger.warning(f"Validation failed, attempting auto-fix: {ve}")
            success, data, fix_repairs = AutoRepair.auto_fix_validation_error(data, ve)
            repairs_applied.extend(fix_repairs)
            
            if success:
                # Try validation again
                document = Document(**data)
            else:
                raise ve
        
        # Render document
        pdf_bytes = render_document(document)
        
        render_time = time.time() - start_time
        
        if repairs_applied:
            logger.info(f"✓ Document repaired and rendered: {create_repair_summary(repairs_applied)}")
        
        logger.info(f"Rendered document with {len(document.blocks)} blocks in {render_time:.3f}s")
        
        # Return PDF with repair info in headers
        headers = {
            "Content-Disposition": f'attachment; filename="{document.meta.title or "document"}.pdf"',
            "X-Render-Time": f"{render_time:.3f}"
        }
        
        if repairs_applied:
            headers["X-Auto-Repairs"] = str(len(repairs_applied))
            headers["X-Repairs-Summary"] = create_repair_summary(repairs_applied)[:200]
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers=headers
        )
    
    except ValidationError as e:
        logger.error(f"Validation error (could not auto-fix): {str(e)}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Rendering error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rendering error: {str(e)}")


@app.post("/render-base64")
async def render_pdf_base64(request: Request, raw_body: str = Body(..., media_type="application/json")) -> Dict[str, Any]:
    """
    Render a document to PDF and return as base64-encoded JSON with auto-repair.
    
    Useful for API clients (like ChatGPT) that cannot handle binary PDF responses.
    
    Args:
        request: FastAPI request object
        raw_body: Raw request body (for auto-repair)
        
    Returns:
        JSON with base64-encoded PDF and metadata
        
    Raises:
        HTTPException: On validation or rendering errors
    """
    repairs_applied = []
    
    try:
        start_time = time.time()
        
        # Try to parse and repair JSON
        success, repaired_json, error = AutoRepair.repair_json(raw_body)
        if not success:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {error}")
        
        if repaired_json != raw_body:
            repairs_applied.append("JSON auto-repaired")
        
        # Parse JSON
        data = json.loads(repaired_json)
        
        # Repair document structure
        success, data, structure_repairs = AutoRepair.repair_document_structure(data)
        repairs_applied.extend(structure_repairs)
        
        # Try to validate with Pydantic
        try:
            document = Document(**data)
        except ValidationError as ve:
            logger.warning(f"Validation failed, attempting auto-fix: {ve}")
            success, data, fix_repairs = AutoRepair.auto_fix_validation_error(data, ve)
            repairs_applied.extend(fix_repairs)
            
            if success:
                document = Document(**data)
            else:
                raise ve
        
        # Render document
        pdf_bytes = render_document(document)
        
        render_time = time.time() - start_time
        
        if repairs_applied:
            logger.info(f"✓ Document repaired and rendered: {create_repair_summary(repairs_applied)}")
        
        logger.info(f"Rendered document (base64) with {len(document.blocks)} blocks in {render_time:.3f}s")
        
        # Encode to base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # Return JSON with repair info
        result = {
            "success": True,
            "pdf_base64": pdf_base64,
            "filename": f"{document.meta.title or 'document'}.pdf",
            "size_bytes": len(pdf_bytes),
            "render_time_seconds": round(render_time, 3),
            "message": "PDF generated successfully. Decode pdf_base64 to get the binary PDF."
        }
        
        if repairs_applied:
            result["auto_repairs"] = {
                "count": len(repairs_applied),
                "summary": create_repair_summary(repairs_applied),
                "details": repairs_applied
            }
        
        return result
    
    except ValidationError as e:
        logger.error(f"Validation error (could not auto-fix): {str(e)}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Rendering error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rendering error: {str(e)}")


@app.post("/render-url")
async def render_pdf_url(request: Request, raw_body: str = Body(..., media_type="application/json")) -> Dict[str, Any]:
    """
    Render a document to PDF and return a temporary download URL with auto-repair.
    
    The PDF is hosted for 1 hour and then automatically deleted.
    Perfect for ChatGPT and other API clients.
    
    Args:
        request: FastAPI request object (to build absolute URL)
        raw_body: Raw request body (for auto-repair)
        
    Returns:
        JSON with temporary URL to download the PDF
        
    Raises:
        HTTPException: On validation or rendering errors
    """
    repairs_applied = []
    
    try:
        start_time = time.time()
        
        # Try to parse and repair JSON
        success, repaired_json, error = AutoRepair.repair_json(raw_body)
        if not success:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {error}")
        
        if repaired_json != raw_body:
            repairs_applied.append("JSON auto-repaired")
        
        # Parse JSON
        data = json.loads(repaired_json)
        
        # Repair document structure
        success, data, structure_repairs = AutoRepair.repair_document_structure(data)
        repairs_applied.extend(structure_repairs)
        
        # Try to validate with Pydantic
        try:
            document = Document(**data)
        except ValidationError as ve:
            logger.warning(f"Validation failed, attempting auto-fix: {ve}")
            success, data, fix_repairs = AutoRepair.auto_fix_validation_error(data, ve)
            repairs_applied.extend(fix_repairs)
            
            if success:
                document = Document(**data)
            else:
                raise ve
        
        # Render document
        pdf_bytes = render_document(document)
        
        render_time = time.time() - start_time
        
        if repairs_applied:
            logger.info(f"✓ Document repaired and rendered: {create_repair_summary(repairs_applied)}")
        
        logger.info(f"Rendered document (URL) with {len(document.blocks)} blocks in {render_time:.3f}s")
        
        # Generate unique filename
        file_id = str(uuid.uuid4())[:8]
        filename = f"{file_id}_{document.meta.title or 'document'}.pdf".replace(" ", "_")
        filepath = TEMP_DIR / filename
        
        # Save PDF to temp directory
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        
        # Build absolute URL
        base_url = str(request.base_url).rstrip('/')
        pdf_url = f"{base_url}/temp-pdfs/{filename}"
        
        # Return JSON with URL and repair info
        result = {
            "success": True,
            "pdf_url": pdf_url,
            "filename": f"{document.meta.title or 'document'}.pdf",
            "size_bytes": len(pdf_bytes),
            "render_time_seconds": round(render_time, 3),
            "expires_in": "1 hour",
            "message": "PDF generated successfully. Download it from pdf_url before it expires."
        }
        
        if repairs_applied:
            result["auto_repairs"] = {
                "count": len(repairs_applied),
                "summary": create_repair_summary(repairs_applied),
                "details": repairs_applied
            }
        
        return result
    
    except ValidationError as e:
        logger.error(f"Validation error (could not auto-fix): {str(e)}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
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
