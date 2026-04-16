"""
FastAPI application for generating financial presentation PDFs.
Deploy to Railway with: railway up
"""
import time
from datetime import datetime
from pathlib import Path
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from financial_models import (
    GenerateContentRequest,
    GenerateContentResponse,
    GeneratePDFRequest,
    GeneratePDFResponse,
)
from commentary import generate_slide_commentary
from generate_real_charts_pdf import generate_pdf_from_slides

app = FastAPI(
    title="Financial Presentation Generator API",
    description="Generate professional financial presentations from structured KPI data",
    version="2.0.0",
)

# CORS — allow all origins (restrict to known domains in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated PDFs at /static/<filename>
Path("static").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Financial Presentation Generator",
        "version": "2.0.0",
        "endpoints": {
            "POST /generate-slide-content": "Generate AI commentary for KPI slides",
            "POST /generate": "Render structured slides to PDF",
            "GET /download/{filename}": "Download a generated PDF",
            "GET /health": "Liveness check",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ── POST /generate-slide-content ──────────────────────────────────────────────

@app.post("/generate-slide-content", response_model=GenerateContentResponse)
async def generate_slide_content(request: GenerateContentRequest):
    """
    Generate AI commentary (title, description, bullet_points) for each KPI slide
    and its root causes. Fires all DeepSeek calls in parallel via ThreadPoolExecutor.

    Target latency: < 15 seconds.
    """
    t0 = time.time()
    print(f"\n{'='*60}")
    print(f"📝 POST /generate-slide-content  —  {len(request.selected_slides)} slides")
    print(f"{'='*60}")

    try:
        slides = generate_slide_commentary(
            financial_text=request.financial_text,
            slides_input=request.selected_slides,
        )
        elapsed = time.time() - t0
        print(f"✅ Commentary generated in {elapsed:.2f}s")
        return GenerateContentResponse(slides=slides)

    except Exception as e:
        import traceback
        print(f"❌ /generate-slide-content error: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Commentary generation failed: {type(e).__name__}: {str(e)}",
        )


# ── POST /generate ────────────────────────────────────────────────────────────

@app.post("/generate", response_model=GeneratePDFResponse)
async def generate_pdf(request: GeneratePDFRequest):
    """
    Render structured slide data (user-edited titles, descriptions, bullet points,
    root cause charts) into a downloadable PDF presentation.

    Target latency: < 60 seconds.
    """
    t0 = time.time()
    print(f"\n{'='*60}")
    print(f"🚀 POST /generate  —  {len(request.slides)} slides")
    print(f"📄 Title: {request.report_title}")
    print(f"{'='*60}")

    try:
        filename = await generate_pdf_from_slides(request)
        elapsed = time.time() - t0
        print(f"✅ PDF ready: {filename}  ({elapsed:.2f}s)")
        return GeneratePDFResponse(pdf_url=f"/static/{filename}")

    except Exception as e:
        import traceback
        print(f"❌ /generate error: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {type(e).__name__}: {str(e)}",
        )


# ── GET /download/{filename} ──────────────────────────────────────────────────

@app.get("/download/{filename}")
async def download_pdf(filename: str):
    """Download a generated PDF by filename."""
    file_path = Path("static") / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
