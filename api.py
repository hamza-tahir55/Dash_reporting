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
    generate_dashboard_html_with_real_data,
    generate_cashflow_waterfall_html,
    generate_root_cause_html,
)
from financial_models import (
    GenerateSlideContentRequest,
    GenerateSlideContentResponse,
    SlideContent,
    RootCauseContent,
)
from openai_service import AIService
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
    report_title: Optional[str] = "Financial Analysis Report"
    report_subtitle: Optional[str] = "Comprehensive Financial Overview"
    company_name: Optional[str] = "DashAnalytix"
    organization_name: Optional[str] = "Financial Analysis"
    contact_phone: Optional[str] = "+1-234-567-8900"
    contact_email: Optional[str] = "contact@DashAnalytix.com"
    contact_website: Optional[str] = "www.app.DashAnalytix.com"
    presentation_date: Optional[str] = None
    prepared_by: Optional[str] = "Analytics Team"
    logo_url: Optional[str] = None
    dash_logo: Optional[bool] = True
    # When provided, skip AI extraction and use these pre-written slides directly
    slides: Optional[List[SlideContent]] = None
    

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


@app.post("/generate-slide-content", response_model=GenerateSlideContentResponse)
async def generate_slide_content(request: GenerateSlideContentRequest):
    """
    Stage 1 of the new flow: given the AI summary and the KPIs + root causes
    the user selected, return AI-generated descriptions and bullet points for
    each KPI and each root cause.  The frontend shows these as editable cards
    before the user clicks "Create Report".

    chart_data from each RootCauseSelection is passed through unchanged so the
    frontend can send it back in POST /generate.
    """
    import asyncio
    import json
    import re

    try:
        # Build a readable list of what the user selected
        selection_lines = []
        for sel in request.selected_slides:
            selection_lines.append(f"KPI: {sel.kpi_name}")
            for rc in sel.root_causes:
                selection_lines.append(f"  Root Cause: {rc.name}")
        selection_text = "\n".join(selection_lines)

        prompt = f"""You are a financial analyst writing slide content for a business presentation.

Based ONLY on the financial summary below, generate descriptions and bullet-point insights
for each KPI and root cause listed under "Selected items".

Rules:
- For each KPI: write a 2-3 sentence description and 3-4 bullet points (factual, data-driven).
- For each root cause within a KPI: write a 1-2 sentence description and 2-3 bullet points.
- Bullet points must start with a capital letter and end without a period.
- Use the actual numbers from the summary where relevant.
- Tone: concise, professional, executive-ready.

Financial Summary:
{request.financial_text}

Selected items:
{selection_text}

Return ONLY valid JSON — no markdown fences, no extra text — in this exact shape:
{{
  "slides": [
    {{
      "kpi_name": "Income",
      "title": "Income Performance Analysis",
      "description": "...",
      "bullet_points": ["...", "...", "..."],
      "root_causes": [
        {{
          "name": "Top Customers by Value Spend",
          "description": "...",
          "bullet_points": ["...", "..."]
        }}
      ]
    }}
  ]
}}"""

        ai_service = AIService()
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(
            None,
            lambda: ai_service.generate_completion(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000,
            ),
        )

        # Strip markdown fences if model wraps output
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        parsed = json.loads(cleaned)

        # Build lookup: kpi_name → {rc_name → chart_data} so we can reattach
        chart_lookup: dict = {}
        for sel in request.selected_slides:
            chart_lookup[sel.kpi_name] = {rc.name: rc.chart_data for rc in sel.root_causes}

        slides: List[SlideContent] = []
        for sd in parsed.get("slides", []):
            kpi = sd["kpi_name"]
            root_causes = []
            for rc_d in sd.get("root_causes", []):
                root_causes.append(
                    RootCauseContent(
                        name=rc_d["name"],
                        description=rc_d.get("description", ""),
                        bullet_points=rc_d.get("bullet_points", []),
                        chart_data=chart_lookup.get(kpi, {}).get(rc_d["name"]),
                    )
                )
            slides.append(
                SlideContent(
                    kpi_name=kpi,
                    title=sd.get("title", f"{kpi} Analysis"),
                    description=sd.get("description", ""),
                    bullet_points=sd.get("bullet_points", []),
                    root_causes=root_causes,
                )
            )

        return GenerateSlideContentResponse(slides=slides)

    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Error generating slide content: {str(e)}\n{traceback.format_exc()}",
        )


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
        print(f"🗂️  Mode: {'Pre-written slides' if request.slides else 'AI extraction'}")
        print(f"{'='*60}")

        # Step 1: Setup
        step_start = time.time()
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, "slides")
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize variables to avoid UnboundLocalError
        pdf_files = []
        sorted_files = [] 
        step_start = log_step("1. Setup & Directory Creation", step_start)

        # ------------------------------------------------------------------ #
        # BRANCH A — pre-written slides provided by the frontend              #
        # (user went through KPI-selection + description editing flow)        #
        # ------------------------------------------------------------------ #
        if request.slides:
            print(f"📋 Using {len(request.slides)} pre-written slides from request")
            step_start = log_step("2. Skip AI extraction (slides provided)", step_start)

            # Build the title slide data dict
            title_data = {
                'type': 'title',
                'title': request.report_title or "Financial Analysis Report",
                'subtitle': request.report_subtitle or "Comprehensive Financial Overview",
                'company_name': request.company_name or "DashAnalytix",
                'org_name': request.organization_name or "Financial Analysis",
                'organization': request.organization_name or "Financial Analysis",
                'phone': request.contact_phone or "+1-234-567-8900",
                'email': request.contact_email or "contact@DashAnalytix.com",
                'website': request.contact_website or "www.app.DashAnalytix.com",
                'date': request.presentation_date or datetime.now().strftime("%B %Y"),
                'prepared_by': request.prepared_by or "Analytics Team",
                'logo_url': request.logo_url,
                'dash_logo': request.dash_logo,
            }

            # Each KPI produces 1 KPI slide + (optionally) 1 root-cause slide
            html_slides: List[dict] = []  # list of {'html': str, 'has_chart': bool}

            html_slides.append({'html': generate_title_html(title_data), 'has_chart': False})

            for slide in request.slides:
                print(f"  📊 Building KPI slide: {slide.kpi_name}")

                kpi_data = {
                    'type': 'statistic',
                    'title': slide.title,
                    'subtitle': slide.description,
                    'value': '',
                    'label': '',
                    'bullets': slide.bullet_points,
                    'chart_data': [],
                    'kpi_prev_percent': '',
                    'kpi_prev_label': '',
                    'kpi_yoy_percent': '',
                    'kpi_yoy_label': '',
                }
                html_slides.append({
                    'html': generate_statistic_html_with_real_chart(kpi_data),
                    'has_chart': False,  # no TSX chart data → no canvas to wait for
                })

                if slide.root_causes:
                    print(f"     🔍 Building root-cause slide ({len(slide.root_causes)} causes)")
                    rc_list = [rc.model_dump() for rc in slide.root_causes]
                    html_slides.append({
                        'html': generate_root_cause_html(
                            kpi_name=slide.kpi_name,
                            root_causes=rc_list,
                            kpi_description=slide.description,
                        ),
                        'has_chart': any(
                            rc.chart_data and rc.chart_data.labels
                            for rc in slide.root_causes
                        ),
                    })

            step_start = log_step("3. HTML Slide Generation", step_start)

            # Render all HTML slides to PDF via Playwright
            pdf_output = os.path.join(temp_dir, "presentation.pdf")
            browser_start = time.time()
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    viewport={"width": 1280, "height": 720}, device_scale_factor=2
                )
                print(f"🌐 Browser initialised in {time.time() - browser_start:.2f}s")

                for i, slide_info in enumerate(html_slides, 1):
                    slide_start = time.time()
                    await page.set_content(slide_info['html'])
                    await page.wait_for_load_state('networkidle')

                    if slide_info['has_chart']:
                        await page.wait_for_timeout(6000)
                        await page.wait_for_selector('canvas', timeout=15000)
                    else:
                        await page.wait_for_timeout(1000)

                    slide_pdf = os.path.join(temp_dir, f"slide_{i}.pdf")
                    await page.pdf(
                        path=slide_pdf,
                        width="1280px",
                        height="720px",
                        print_background=True,
                        prefer_css_page_size=True,
                    )
                    pdf_files.append(slide_pdf)
                    print(f"   ✅ Slide {i} done in {time.time() - slide_start:.2f}s")

                await browser.close()

            step_start = log_step("4. PDF Generation (Browser)", step_start)

        # ------------------------------------------------------------------ #
        # BRANCH B — original AI-extraction flow                             #
        # ------------------------------------------------------------------ #
        else:
            # Step 2: DeepSeek Preprocessing
            print(f"🧠 DeepSeek preprocessing input text...")
            generator = FinancialTSXGenerator()

            print(f"🚀 Using ThreadPoolExecutor concurrent AI processing...")
            parsed_data = await generator.process_financial_data_with_threadpool_concurrency(
                raw_financial_text=request.financial_text,
                output_dir=output_dir,
            )
            step_start = log_step("2-3. Concurrent AI Processing & Data Extraction", step_start)

            print(f"\n{'='*60}")
            print(f"🔍 DEBUG: AI EXTRACTION RESULTS")
            print(f"{'='*60}")
            print(f"Metrics extracted: {len(parsed_data.get('metrics', []))}")
            if parsed_data.get('metrics'):
                for i, m in enumerate(parsed_data.get('metrics', []), 1):
                    print(f"  {i}. {m.get('name', 'UNNAMED')}")
            else:
                print(f"⚠️  WARNING: NO METRICS EXTRACTED!")
            print(f"{'='*60}\n")

            from pathlib import Path as PathLib
            output_path = PathLib(output_dir)
            all_tsx_files = []

            print("📝 Generating Title Slide...")
            title_file = generator._generate_title_slide(parsed_data, output_path)
            all_tsx_files.append(title_file)

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

            print("📊 Generating Statistic Slides...")
            for metric in parsed_data.get("metrics", []):
                stat_file = generator._generate_statistic_slide(metric, output_path)
                all_tsx_files.append(stat_file)

            print(f"\n✅ Generated {len(all_tsx_files)} TSX slide components!")
            step_start = log_step("3. TSX File Generation", step_start)

            print(f"🎯 Organising slides...")
            tsx_files = _filter_to_ten_slides(all_tsx_files, output_dir)
            step_start = log_step("4. Slide Organisation", step_start)

            if not tsx_files:
                raise HTTPException(status_code=500, detail="Failed to generate TSX slides")

            pdf_output = os.path.join(temp_dir, "presentation.pdf")
            sorted_files = [Path(f) for f in tsx_files]

            browser_start = time.time()
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    viewport={"width": 1280, "height": 720}, device_scale_factor=2
                )
                print(f"🌐 Browser initialised in {time.time() - browser_start:.2f}s")

                for i, tsx_file in enumerate(sorted_files, 1):
                    slide_start = time.time()
                    data = parse_tsx_with_data(tsx_file)

                    print(f"📊 Processing Slide {i}/{len(sorted_files)}: {tsx_file.name}")
                    print(f"   Title: {data.get('title', 'N/A')}")
                    print(f"   Chart Data Points: {len(data.get('chart_data', []))}")

                    if data['type'] == 'title':
                        data['title'] = request.report_title or "Financial Analysis Report"
                        data['subtitle'] = request.report_subtitle or "Comprehensive Financial Overview"
                        data['company_name'] = request.company_name or "DashAnalytix"
                        data['org_name'] = request.organization_name or "Financial Analysis"
                        data['organization'] = request.organization_name or "Financial Analysis"
                        data['phone'] = request.contact_phone or "+1-234-567-8900"
                        data['email'] = request.contact_email or "contact@DashAnalytix.com"
                        data['website'] = request.contact_website or "www.app.DashAnalytix.com"
                        data['date'] = request.presentation_date or datetime.now().strftime("%B %Y")
                        data['prepared_by'] = request.prepared_by or "Analytics Team"
                        data['logo_url'] = request.logo_url
                        data['dash_logo'] = request.dash_logo
                        html = generate_title_html(data)
                    elif 'Dashboard' in tsx_file.name:
                        all_metrics_data = []
                        all_tsx_paths = [Path(f) for f in all_tsx_files]
                        for f in all_tsx_paths:
                            if f.name != tsx_file.name and 'Title' not in f.name and 'Dashboard' not in f.name:
                                metric_data = parse_tsx_with_data(f)
                                all_metrics_data.append(metric_data)
                        html = generate_dashboard_html_with_real_data(all_metrics_data)
                    elif data['type'] == 'comparison':
                        html = generate_comparison_html_with_real_charts(data)
                    else:
                        if 'cash flow' in data.get('title', '').lower():
                            print(f"    💧 Detected Cash Flow - using waterfall chart")
                            html = generate_cashflow_waterfall_html(data)
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
                        prefer_css_page_size=True,
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
        print(f"📊 Slides generated: {len(pdf_files)}")
        # print(f"💰 Provider: {config.provider}")
        print(f"{'='*60}\n")
        
        return GeneratePDFResponse(
            message=f"PDF generated successfully in {total_time:.2f}s",
            pdf_url=f"/download/{final_pdf.name}",
            slides_count=len(pdf_files)
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
