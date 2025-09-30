"""
FastAPI application for generating financial presentation PDFs.
Deploy to Railway with: railway up
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import tempfile
from pathlib import Path
from datetime import datetime
import shutil

from financial_tsx_generator import FinancialTSXGenerator
from playwright.async_api import async_playwright
from generate_real_charts_pdf import (
    parse_tsx_with_data,
    generate_title_html,
    generate_statistic_html_with_real_chart,
    generate_comparison_html_with_real_charts
)
from PyPDF2 import PdfMerger

app = FastAPI(
    title="Financial Presentation Generator API",
    description="Generate professional financial presentations from text",
    version="1.0.0"
)


class FinancialDataRequest(BaseModel):
    """Request model for financial data."""
    financial_text: str
    report_title: Optional[str] = "Financial Analysis Report"        # ← Default title
    report_subtitle: Optional[str] = "Comprehensive Financial Overview"  # ← Default subtitle
    organization_name: Optional[str] = "Financial Analysis"          # ← Default org name
    contact_phone: Optional[str] = "+1-234-567-8900"                # ← Default phone
    contact_email: Optional[str] = "contact@DashAnalytix.com" # ← Default email
    contact_website: Optional[str] = "www.app.DashAnalytix.com"   # ← Default website
    presentation_date: Optional[str] = None  # Auto-generates current month/year
    

class GeneratePDFResponse(BaseModel):
    """Response model."""
    message: str
    pdf_url: str
    slides_count: int


def _filter_to_ten_slides(all_files: List[str], output_dir: str) -> List[str]:
    """Filter generated slides to exactly 10 in specific order."""
    from pathlib import Path
    
    print(f"   📋 All generated files:")
    for f in all_files:
        print(f"      - {Path(f).name}")
    
    # Define the 10-slide structure
    slide_order = [
        'Title',                    # 1. Title slide
        'Income',                   # 2. Income/Revenue
        'Cost',                     # 3. Cost of Sales
        'Expense',                  # 4. Operating Expenses
        'Gross',                    # 5. Gross Profit
        'EBITDA',                   # 6. EBITDA
        'Net',                      # 7. Net Income
        'Collection',               # 8. Customer Collection Days
        'Payment',                  # 9. Supplier Payment Days
        'Inventory'                 # 10. Inventory Days
    ]
    
    selected_files = []
    
    for i, pattern in enumerate(slide_order):
        # Single pattern match
        for file in all_files:
            if pattern in Path(file).name and file not in selected_files:
                selected_files.append(file)
                print(f"   ✅ Slide {i+1}: {Path(file).name}")
                break
    
    print(f"   📊 Selected {len(selected_files)} slides from {len(all_files)} generated")
    
    # If we don't have enough slides, return what we have
    if len(selected_files) == 0:
        print(f"   ⚠️  No slides matched filters, returning all files")
        return all_files[:10]  # Return first 10
    
    return selected_files


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Financial Presentation Generator",
        "version": "1.0.0",
        "endpoints": {
            "POST /generate": "Generate PDF from financial text",
            "GET /health": "Health check"
        }
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/generate", response_model=GeneratePDFResponse)
async def generate_presentation(request: FinancialDataRequest):
    """
    Generate a financial presentation PDF from text.
    
    Example payload:
    ```json
    {
        "financial_text": "Income peaked at $155,815 in Dec 2020...",
        "report_title": "Q3 2024 Financial Report",
        "report_subtitle": "May 2019 to Sep 2024"
    }
    ```
    """
    try:
        # Create temporary directory for this request
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, "slides")
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: Parse financial data and generate TSX slides
        print(f"📊 Generating TSX slides...")
        generator = FinancialTSXGenerator()
        
        # This returns parsed JSON data, not file paths
        parsed_data = generator.generate_financial_slides(
            financial_text=request.financial_text,
            output_dir=output_dir
        )
        
        # Generate actual TSX files from parsed data
        from pathlib import Path as PathLib
        output_path = PathLib(output_dir)
        all_tsx_files = []
        
        # Generate title slide
        print("📝 Generating Title Slide...")
        title_file = generator._generate_title_slide(parsed_data, output_path)
        all_tsx_files.append(title_file)
        
        # Generate statistic slides for each metric
        print("📊 Generating Statistic Slides...")
        for metric in parsed_data.get("metrics", []):
            stat_file = generator._generate_statistic_slide(metric, output_path)
            all_tsx_files.append(stat_file)
        
        # Generate comparison slide if data exists
        if parsed_data.get("comparisons"):
            print("📈 Generating Comparison Slide...")
            comp_file = generator._generate_dual_chart_slide(parsed_data["comparisons"], output_path)
            all_tsx_files.append(comp_file)
        
        print(f"\n✅ Generated {len(all_tsx_files)} TSX slide components!")
        
        # Step 1.5: Filter to only 10 slides in specific order
        print(f"🎯 Filtering to 10-slide structure...")
        tsx_files = _filter_to_ten_slides(all_tsx_files, output_dir)
        
        if not tsx_files:
            raise HTTPException(status_code=500, detail="Failed to generate TSX slides")
        
        # Step 2: Generate PDF from TSX slides
        print(f"📄 Generating PDF...")
        pdf_output = os.path.join(temp_dir, "presentation.pdf")
        
        # Use filtered files (already in correct order: Title, Income, Costs, Profit, WC)
        sorted_files = [Path(f) for f in tsx_files]
        
        # Generate PDFs using async Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
            pdf_files = []
            
            for tsx_file in sorted_files:
                data = parse_tsx_with_data(tsx_file)
                
                # Debug: Print parsed data
                print(f"📊 Slide: {tsx_file.name}")
                print(f"   Title: {data.get('title', 'N/A')}")
                print(f"   Chart Data Points: {len(data.get('chart_data', []))}")
                if data.get('chart_data'):
                    print(f"   First Data Point: {data['chart_data'][0] if data['chart_data'] else 'None'}")
                
                # Add custom data from request
                if data['type'] == 'title':
                    data['title'] = request.report_title
                    data['subtitle'] = request.report_subtitle
                    data['org'] = request.organization_name
                    data['phone'] = request.contact_phone
                    data['email'] = request.contact_email
                    data['website'] = request.contact_website
                    data['date'] = request.presentation_date or datetime.now().strftime("%B %Y")
                    html = generate_title_html(data)
                elif data['type'] == 'comparison':
                    html = generate_comparison_html_with_real_charts(data)
                else:
                    html = generate_statistic_html_with_real_chart(data)
                
                await page.set_content(html)
                await page.wait_for_load_state('networkidle')
                
                if data['type'] != 'title':
                    await page.wait_for_timeout(6000)
                    await page.wait_for_selector('canvas', timeout=15000)
                else:
                    await page.wait_for_timeout(1000)
                
                slide_pdf = os.path.join(temp_dir, f"slide_{len(pdf_files)}.pdf")
                await page.pdf(
                    path=slide_pdf,
                    width="1280px",
                    height="720px",
                    print_background=True,
                    prefer_css_page_size=True
                )
                pdf_files.append(slide_pdf)
            
            await browser.close()
        
        # Merge PDFs
        merger = PdfMerger()
        for pdf_file in pdf_files:
            merger.append(pdf_file)
        merger.write(pdf_output)
        merger.close()
        
        # Check if PDF was created
        if not os.path.exists(pdf_output):
            raise HTTPException(status_code=500, detail="PDF file not created")
        
        # Save PDF to static directory for serving
        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_pdf = static_dir / f"presentation_{timestamp}.pdf"
        
        shutil.copy(pdf_output, str(final_pdf))
        
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return GeneratePDFResponse(
            message="PDF generated successfully",
            pdf_url=f"/download/{final_pdf.name}",
            slides_count=len(sorted_files)
        )
        
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"❌ Error: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/download/{filename}")
async def download_pdf(filename: str):
    """Download generated PDF."""
    file_path = Path("static") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
