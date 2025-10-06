"""
FastAPI application for generating financial presentation PDFs.
Deploy to Railway with: railway up
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
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
    generate_comparison_html_with_real_charts,
    generate_dashboard_html_with_real_data
)
from PyPDF2 import PdfMerger

app = FastAPI(
    title="Financial Presentation Generator API",
    description="Generate professional financial presentations from text",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
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


def _filter_to_six_slides(all_files: List[str], output_dir: str) -> List[str]:
    """Filter to exactly 6 slides: Title + Dashboard + 4 specific detailed metrics."""
    from pathlib import Path
    
    print(f"   📋 All generated files:")
    for f in all_files:
        print(f"      - {Path(f).name}")
    
    # ONLY these 4 metrics get detailed slides (slides 3-6)
    detailed_metrics = [
        'Income',           # Slide 3: Income detailed slide
        'Gross',            # Slide 4: Gross Profit detailed slide  
        'Net',              # Slide 5: Net Income detailed slide
        'Cash'              # Slide 6: Cash Balance detailed slide
    ]
    
    selected_files = []
    
    # Slide 1: Title slide (always first)
    for file in all_files:
        if 'Title' in Path(file).name:
            selected_files.append(file)
            print(f"   ✅ Slide 1: {Path(file).name} (Title)")
            break
    
    # Slide 2: Dashboard slide (always second)
    for file in all_files:
        if 'Dashboard' in Path(file).name:
            selected_files.append(file)
            print(f"   ✅ Slide 2: {Path(file).name} (Business Health Dashboard)")
            break
    
    # Slides 3-6: Only the 4 specific detailed metrics
    for i, pattern in enumerate(detailed_metrics, 3):
        for file in all_files:
            if pattern in Path(file).name and file not in selected_files:
                selected_files.append(file)
                print(f"   ✅ Slide {i}: {Path(file).name} (Detailed {pattern})")
                break
        else:
            print(f"   ⚠️  Slide {i}: No {pattern} metric found - will be skipped")
    
    # Log which metrics will be dashboard-only
    dashboard_metrics = []
    for file in all_files:
        file_name = Path(file).name
        if not any(pattern in file_name for pattern in ['Title', 'Dashboard'] + detailed_metrics):
            if not any(excluded in file_name for excluded in ['Title', 'Dashboard']):
                dashboard_metrics.append(file_name)
    
    if dashboard_metrics:
        print(f"   📊 Dashboard-only metrics ({len(dashboard_metrics)}):")
        for metric in dashboard_metrics:
            print(f"      - {metric}")
    
    print(f"   🎯 Final structure: {len(selected_files)} slides (Title + Dashboard + {len(selected_files)-2} detailed)")
    
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
        
        # DEBUG: Print what AI extracted
        print(f"\n{'='*60}")
        print(f"🔍 DEBUG: AI EXTRACTION RESULTS")
        print(f"{'='*60}")
        print(f"Metrics extracted: {len(parsed_data.get('metrics', []))}")
        print(f"Comparisons: {'YES' if parsed_data.get('comparisons') else 'NO'}")
        if parsed_data.get('metrics'):
            print(f"\nMetric names:")
            for i, m in enumerate(parsed_data.get('metrics', []), 1):
                print(f"  {i}. {m.get('name', 'UNNAMED')}")
        else:
            print(f"\n⚠️  WARNING: NO METRICS EXTRACTED!")
            print(f"   This means the AI could not parse your financial_text.")
            print(f"   Check if financial_text is being sent correctly.")
        print(f"{'='*60}\n")
        
        # Generate actual TSX files from parsed data
        from pathlib import Path as PathLib
        output_path = PathLib(output_dir)
        all_tsx_files = []
        
        # Generate title slide
        print("📝 Generating Title Slide...")
        title_file = generator._generate_title_slide(parsed_data, output_path)
        all_tsx_files.append(title_file)
        
        # Generate dashboard slide (summary of all metrics)
        print("🏢 Generating Business Health Dashboard...")
        dashboard_file = str(output_path / "BusinessDashboardSlide.tsx")
        dashboard_content = '''import React from "react";
import * as z from "zod";

export const layoutName = "Business Health Dashboard";
export const layoutId = "business-dashboard-slide";
export const layoutDescription = "Comprehensive financial and operational dashboard";

export const Schema = z.object({
  dashboardTitle: z.string().default("Business Health Dashboard"),
  dashboardSubtitle: z.string().default("Comprehensive Financial Analysis"),
  showComparativeAnalysis: z.boolean().default(true),
});

type SchemaType = z.infer<typeof Schema>;

const BusinessDashboardSlide = ({ data }: { data: Partial<SchemaType> }) => {
  return (
    <div className="aspect-video max-w-[1280px] w-full bg-white relative overflow-hidden">
      <div className="text-center p-8">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">
          {data.dashboardTitle || "Business Health Dashboard"}
        </h1>
        <p className="text-xl text-gray-600">
          {data.dashboardSubtitle || "Comprehensive Financial Analysis"}
        </p>
      </div>
    </div>
  );
};

export default BusinessDashboardSlide;'''
        
        with open(dashboard_file, 'w') as f:
            f.write(dashboard_content)
        all_tsx_files.append(dashboard_file)
        print(f"  ✓ Created: {dashboard_file}")
        
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
        
        # Step 1.5: Organize slides - Title + Dashboard + 4 specific detailed metrics only
        print(f"🎯 Organizing slides: Title + Dashboard + 4 detailed metrics...")
        tsx_files = _filter_to_six_slides(all_tsx_files, output_dir)
        
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
                elif 'Dashboard' in tsx_file.name:
                    # Generate dashboard slide with all metrics data
                    all_metrics_data = []
                    for f in sorted_files:
                        if f.name != tsx_file.name and 'Title' not in f.name and 'Dashboard' not in f.name:
                            metric_data = parse_tsx_with_data(f)
                            all_metrics_data.append(metric_data)
                    html = generate_dashboard_html_with_real_data(all_metrics_data)
                elif data['type'] == 'comparison':
                    html = generate_comparison_html_with_real_charts(data)
                else:
                    html = generate_statistic_html_with_real_chart(data)
                
                await page.set_content(html)
                await page.wait_for_load_state('networkidle')
                
                if data['type'] != 'title' and 'Dashboard' not in tsx_file.name:
                    await page.wait_for_timeout(6000)
                    await page.wait_for_selector('canvas', timeout=15000)
                elif 'Dashboard' in tsx_file.name:
                    # Dashboard has multiple charts, wait longer
                    await page.wait_for_timeout(8000)
                    await page.wait_for_selector('canvas', timeout=20000)
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
