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
    company_name: Optional[str] = "DashAnalytix"                     # ← Company name from frontend
    organization_name: Optional[str] = "Financial Analysis"          # ← Default org name
    contact_phone: Optional[str] = "+1-234-567-8900"                # ← Default phone
    contact_email: Optional[str] = "contact@DashAnalytix.com" # ← Default email
    contact_website: Optional[str] = "www.app.DashAnalytix.com"   # ← Default website
    presentation_date: Optional[str] = None  # Auto-generates current month/year
    prepared_by: Optional[str] = "Analytics Team"                   # ← Default prepared by
    logo_url: Optional[str] = None                                  # ← Dynamic logo URL
    

class GeneratePDFResponse(BaseModel):
    """Response model."""
    message: str
    pdf_url: str
    slides_count: int


def _filter_to_ten_slides(all_files: List[str], output_dir: str) -> List[str]:
    """Organize slides with specific flow: Title -> Dashboard -> Income -> Gross Profit -> Net Income -> Cash Flow."""
    from pathlib import Path
    
    print(f"   📋 All generated files:")
    for f in all_files:
        print(f"      - {Path(f).name}")
    
    # New priority order: Title, Dashboard (excluding priority metrics), then 4 priority metrics
    priority_metrics = ['Income', 'Gross', 'Net', 'Cash']  # These get individual slides
    
    # Priority order for organizing slides
    slide_priority = [
        'Title',                    # 1. Title slide (always first)
        'Dashboard',                # 2. Business Health Dashboard (excluding priority metrics)
        'Income',                   # 3. Income/Revenue (individual slide)
        'Gross',                    # 4. Gross Profit (individual slide)
        'Net',                      # 5. Net Income (individual slide)
        'Cash',                     # 6. Cash Balance (individual slide)
    ]
    
    selected_files = []
    
    # First, add slides in priority order
    for i, pattern in enumerate(slide_priority):
        for file in all_files:
            if pattern in Path(file).name and file not in selected_files:
                selected_files.append(file)
                print(f"   ✅ Slide {len(selected_files)}: {Path(file).name}")
                break
    
    # Then add any remaining slides that weren't matched by priority patterns
    # (but skip the priority metrics since they already have individual slides)
    for file in all_files:
        if file not in selected_files:
            file_name = Path(file).name
            # Skip if this file contains any of the priority metrics (they already have individual slides)
            is_priority_metric = any(metric in file_name for metric in priority_metrics)
            if not is_priority_metric:
                selected_files.append(file)
                print(f"   ✅ Slide {len(selected_files)}: {Path(file).name} (additional metric)")
    
    # Limit to only 6 slides as requested
    selected_files = selected_files[:6]
    
    print(f"   📊 Including {len(selected_files)} slides from {len(all_files)} generated")
    print(f"   🎯 Flow: Title -> Dashboard (other KPIs) -> Income -> Gross Profit -> Net Income -> Cash Flow")
    
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
    import time
    
    # Performance monitoring
    total_start_time = time.time()
    step_times = {}
    
    def log_step(step_name: str, start_time: float):
        duration = time.time() - start_time
        step_times[step_name] = duration
        print(f"⏱️  {step_name}: {duration:.2f}s")
        return time.time()
    
    try:
        print(f"\n{'='*60}")
        print(f"🚀 STARTING PRESENTATION GENERATION")
        print(f"📝 Financial text length: {len(request.financial_text)} characters")
        # print(f"🤖 AI Provider: {config.provider}")
        print(f"{'='*60}")
        
        # Step 1: Setup
        step_start = time.time()
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, "slides")
        os.makedirs(output_dir, exist_ok=True)
        step_start = log_step("1. Setup & Directory Creation", step_start)
        
        # Step 2: DeepSeek Preprocessing - Clean and structure the input text
        print(f"🧠 DeepSeek preprocessing input text...")
        generator = FinancialTSXGenerator()
        
        # Use ThreadPoolExecutor concurrent processing for improved performance
        print(f"🚀 Using ThreadPoolExecutor concurrent AI processing to reduce processing time...")
        parsed_data = await generator.process_financial_data_with_threadpool_concurrency(
            raw_financial_text=request.financial_text,
            output_dir=output_dir
        )
        step_start = log_step("2-3. Concurrent AI Processing & Data Extraction", step_start)
        
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
        
        # Step 4: TSX File Generation
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
        
        # Generate comparison slide if data exists (DISABLED)
        # if parsed_data.get("comparisons"):
        #     print("📈 Generating Comparison Slide...")
        #     comp_file = generator._generate_dual_chart_slide(parsed_data["comparisons"], output_path)
        #     all_tsx_files.append(comp_file)
        
        print(f"\n✅ Generated {len(all_tsx_files)} TSX slide components!")
        step_start = log_step("3. TSX File Generation", step_start)
        
        # Step 4: Organize slides - include all extracted metrics
        print(f"🎯 Organizing slides for all extracted metrics...")
        tsx_files = _filter_to_ten_slides(all_tsx_files, output_dir)
        step_start = log_step("4. Slide Organization", step_start)
        
        if not tsx_files:
            raise HTTPException(status_code=500, detail="Failed to generate TSX slides")
        
        # Step 5: Generate PDF from TSX slides
        print(f"📄 Generating PDF...")
        pdf_output = os.path.join(temp_dir, "presentation.pdf")
        
        # Use filtered files (already in correct order: Title, Income, Costs, Profit, WC)
        sorted_files = [Path(f) for f in tsx_files]
        
        # Generate PDFs using async Playwright
        browser_start = time.time()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
            pdf_files = []
            
            print(f"🌐 Browser initialized in {time.time() - browser_start:.2f}s")
            
            for i, tsx_file in enumerate(sorted_files, 1):
                slide_start = time.time()
                data = parse_tsx_with_data(tsx_file)
                
                # Debug: Print parsed data
                print(f"📊 Processing Slide {i}/{len(sorted_files)}: {tsx_file.name}")
                print(f"   Title: {data.get('title', 'N/A')}")
                print(f"   Chart Data Points: {len(data.get('chart_data', []))}")
                if data.get('chart_data'):
                    print(f"   First Data Point: {data['chart_data'][0] if data['chart_data'] else 'None'}")
                
                # Add custom data from request
                if data['type'] == 'title':
                    data['title'] = request.report_title or "Financial Analysis Report"
                    data['subtitle'] = request.report_subtitle or "Comprehensive Financial Overview"
                    data['company_name'] = request.company_name or "DashAnalytix"
                    data['org_name'] = request.organization_name or "Financial Analysis"
                    data['organization'] = request.organization_name or "Financial Analysis"  # For footer consistency
                    data['phone'] = request.contact_phone or "+1-234-567-8900"
                    data['email'] = request.contact_email or "contact@DashAnalytix.com"
                    data['website'] = request.contact_website or "www.app.DashAnalytix.com"
                    data['date'] = request.presentation_date or datetime.now().strftime("%B %Y")
                    data['prepared_by'] = request.prepared_by or "Analytics Team"
                    data['logo_url'] = request.logo_url
                    html = generate_title_html(data)
                elif 'Dashboard' in tsx_file.name:
                    # Generate dashboard slide with all metrics data from ALL generated files
                    all_metrics_data = []
                    # Use all_tsx_files instead of sorted_files to get complete data for dashboard
                    all_tsx_paths = [Path(f) for f in all_tsx_files]
                    for f in all_tsx_paths:
                        if f.name != tsx_file.name and 'Title' not in f.name and 'Dashboard' not in f.name:
                            metric_data = parse_tsx_with_data(f)
                            all_metrics_data.append(metric_data)
                    html = generate_dashboard_html_with_real_data(all_metrics_data)
                elif data['type'] == 'comparison':
                    html = generate_comparison_html_with_real_charts(data)
                else:
                    html = generate_statistic_html_with_real_chart(data)
                
                html_start = time.time()
                await page.set_content(html)
                await page.wait_for_load_state('networkidle')
                print(f"   📄 HTML loaded in {time.time() - html_start:.2f}s")
                
                render_start = time.time()
                if data['type'] != 'title' and 'Dashboard' not in tsx_file.name:
                    await page.wait_for_timeout(6000)
                    await page.wait_for_selector('canvas', timeout=15000)
                elif 'Dashboard' in tsx_file.name:
                    # Dashboard has multiple charts, wait longer
                    await page.wait_for_timeout(8000)
                    await page.wait_for_selector('canvas', timeout=20000)
                else:
                    await page.wait_for_timeout(1000)
                print(f"   🎨 Chart rendering in {time.time() - render_start:.2f}s")
                
                pdf_start = time.time()
                slide_pdf = os.path.join(temp_dir, f"slide_{len(pdf_files)}.pdf")
                await page.pdf(
                    path=slide_pdf,
                    width="1280px",
                    height="720px",
                    print_background=True,
                    prefer_css_page_size=True
                )
                pdf_files.append(slide_pdf)
                print(f"   📑 PDF generation in {time.time() - pdf_start:.2f}s")
                print(f"   ✅ Total slide time: {time.time() - slide_start:.2f}s")
            
            await browser.close()
        
        step_start = log_step("5. PDF Generation (Browser)", step_start)
        
        # Step 6: Merge PDFs
        merge_start = time.time()
        merger = PdfMerger()
        for pdf_file in pdf_files:
            merger.append(pdf_file)
        merger.write(pdf_output)
        merger.close()
        step_start = log_step("6. PDF Merging", step_start)
        
        # Step 7: File Operations
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
        step_start = log_step("7. File Operations & Cleanup", step_start)
        
        # Final Performance Summary
        total_time = time.time() - total_start_time
        print(f"\n{'='*60}")
        print(f"🎯 PERFORMANCE SUMMARY")
        print(f"{'='*60}")
        for step, duration in step_times.items():
            percentage = (duration / total_time) * 100
            print(f"⏱️  {step}: {duration:.2f}s ({percentage:.1f}%)")
        print(f"{'='*60}")
        print(f"🏁 TOTAL TIME: {total_time:.2f}s")
        print(f"📊 Slides generated: {len(sorted_files)}")
        # print(f"💰 Provider: {config.provider}")
        print(f"{'='*60}\n")
        
        return GeneratePDFResponse(
            message=f"PDF generated successfully in {total_time:.2f}s",
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
