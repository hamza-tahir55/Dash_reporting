"""
PDF slide generation from structured frontend data.
Builds Chart.js HTML pages, renders via Playwright, merges with PyPDF2.
"""
import base64
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

from PyPDF2 import PdfMerger
from playwright.async_api import async_playwright

from financial_models import GeneratePDFRequest, SlidePayload


# ── Logo helper ───────────────────────────────────────────────────────────────

def _get_logo_src(logo_url: str | None, use_dash_logo: bool) -> str | None:
    """Return a src string (data-URI or URL) for the logo, or None."""
    if not use_dash_logo:
        if logo_url:
            return logo_url.strip().strip("`")
        return None
    # Use bundled Dash Analytix logo
    logo_path = Path("assets/logo.png")
    if logo_path.exists():
        data = base64.b64encode(logo_path.read_bytes()).decode()
        return f"data:image/png;base64,{data}"
    return "https://dashanalytix.com/wp-content/uploads/2023/11/logo-color.png"


# ── HTML generators ───────────────────────────────────────────────────────────

def _title_html(req: GeneratePDFRequest) -> str:
    logo_src = _get_logo_src(req.logo_url, req.dash_logo)
    logo_tag = (
        f'<img src="{logo_src}" alt="Logo" class="logo">'
        if logo_src
        else ""
    )

    date_str = req.presentation_date or datetime.now().strftime("%B %Y")

    footer_parts = [p for p in [req.organization_name, req.prepared_by, date_str] if p]
    footer_line = " &nbsp;|&nbsp; ".join(footer_parts)

    contact_parts = []
    if req.contact_email:
        contact_parts.append(f"&#9993; {req.contact_email}")
    if req.contact_phone:
        contact_parts.append(f"&#9742; {req.contact_phone}")
    if req.contact_website:
        contact_parts.append(req.contact_website)
    contact_line = " &nbsp;&nbsp; ".join(contact_parts)

    subtitle_html = (
        f'<p class="subtitle">{req.report_subtitle}</p>'
        if req.report_subtitle
        else ""
    )

    # NOTE: Use radial-gradient backgrounds instead of blur()+border-radius blobs —
    # filter:blur + border-radius:50% renders as geometric outlines in Playwright PDF mode.
    # Also avoid -webkit-background-clip:text / -webkit-text-fill-color:transparent
    # as those make text invisible in Playwright PDF export.
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px; overflow: hidden;
    /* Multi-layer radial gradients replace JS/blur blobs — PDF-safe */
    background-color: #0b1120;
    background-image:
      radial-gradient(ellipse 700px 600px at -5% -10%, rgba(0,212,170,0.22) 0%, transparent 70%),
      radial-gradient(ellipse 600px 500px at 105% 110%, rgba(0,80,220,0.28) 0%, transparent 70%),
      radial-gradient(ellipse 400px 350px at 75% 20%, rgba(100,50,200,0.14) 0%, transparent 65%);
    font-family: 'Segoe UI', Arial, sans-serif;
    color: #ffffff;
    position: relative;
  }}
  /* Decorative geometric accents (PDF-safe, no filter:blur) */
  .geo {{
    position: absolute;
    border: 1px solid rgba(255,255,255,0.07);
  }}
  .geo-1 {{ width: 220px; height: 220px; top: 60px; right: 120px; transform: rotate(15deg); }}
  .geo-2 {{ width: 120px; height: 120px; bottom: 80px; left: 160px; transform: rotate(30deg); }}
  .geo-3 {{
    width: 0; height: 0;
    border: none;
    border-left: 80px solid transparent;
    border-right: 80px solid transparent;
    border-bottom: 140px solid rgba(0,212,170,0.06);
    top: 180px; left: 60px;
  }}
  /* Teal left accent bar */
  .accent-bar {{
    position: absolute; left: 0; top: 0; bottom: 0;
    width: 5px;
    background: linear-gradient(180deg, #00d4aa 0%, #0066ff 100%);
  }}
  /* Main content area */
  .content {{
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    width: 860px;
    display: flex; flex-direction: column; align-items: center; gap: 18px;
  }}
  .logo {{
    height: 52px;
    margin-bottom: 4px;
    object-fit: contain;
  }}
  .tag {{
    display: inline-block;
    font-size: 10px; font-weight: 700; letter-spacing: 3px;
    text-transform: uppercase; color: #00d4aa;
    border: 1px solid rgba(0,212,170,0.35);
    padding: 5px 18px; border-radius: 20px;
  }}
  /* Plain solid-colour heading — avoids invisible gradient-clip text in PDF */
  h1 {{
    font-size: 50px; font-weight: 800; line-height: 1.18;
    color: #ffffff;
    text-shadow: 0 2px 20px rgba(0,0,0,0.5);
  }}
  .divider {{
    width: 56px; height: 3px;
    background: linear-gradient(90deg, #00d4aa, #0066ff);
    border-radius: 2px;
  }}
  .subtitle {{
    font-size: 17px; color: #a0b8d0; font-weight: 400;
    line-height: 1.6; max-width: 620px;
  }}
  /* Footer */
  .footer {{
    position: absolute; bottom: 0; left: 0; right: 0;
    background: rgba(0,0,0,0.25);
    border-top: 1px solid rgba(255,255,255,0.08);
    padding: 16px 60px;
    display: flex; justify-content: space-between; align-items: center;
  }}
  .footer-left {{ font-size: 12px; color: #8a9ab0; }}
  .footer-right {{ font-size: 11px; color: #5a6a7a; }}
</style>
</head>
<body>
  <div class="accent-bar"></div>
  <div class="geo geo-1"></div>
  <div class="geo geo-2"></div>
  <div class="geo geo-3"></div>

  <div class="content">
    {logo_tag}
    <div class="tag">Financial Report</div>
    <h1>{req.report_title}</h1>
    <div class="divider"></div>
    {subtitle_html}
  </div>

  <div class="footer">
    <span class="footer-left">{footer_line}</span>
    <span class="footer-right">{contact_line}</span>
  </div>
</body>
</html>"""


_CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"


def _chart_script(chart_data, canvas_id: str = "myChart") -> str:
    """Build the Chart.js initialisation <script> block."""
    labels_json = json.dumps(chart_data.labels)
    values_json = json.dumps(chart_data.values)
    chart_type = chart_data.chart_type  # "bar" or "line"

    is_bar = chart_type == "bar"
    bg_color = "#00d4aa" if is_bar else "rgba(0,212,170,0.15)"
    fill_config = "false" if is_bar else "true"
    tension = "0" if is_bar else "0.4"
    border_radius = 4 if is_bar else 0
    point_radius = 0 if is_bar else 3

    # Set window.__chartReady = true in animation.onComplete so Playwright
    # can poll for it instead of relying on a fixed timeout.
    return f"""
const ctx = document.getElementById('{canvas_id}').getContext('2d');
new Chart(ctx, {{
  type: '{chart_type}',
  data: {{
    labels: {labels_json},
    datasets: [{{
      label: '',
      data: {values_json},
      backgroundColor: '{bg_color}',
      borderColor: '#00d4aa',
      borderWidth: 2,
      borderRadius: {border_radius},
      fill: {fill_config},
      tension: {tension},
      pointBackgroundColor: '#00d4aa',
      pointRadius: {point_radius},
    }}]
  }},
  options: {{
    animation: {{
      onComplete: function() {{ window.__chartReady = true; }}
    }},
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{
        ticks: {{ color: '#a0aec0', font: {{ size: 11 }}, maxRotation: 45 }},
        grid: {{ color: 'rgba(255,255,255,0.06)' }}
      }},
      y: {{
        ticks: {{ color: '#a0aec0', font: {{ size: 11 }} }},
        grid: {{ color: 'rgba(255,255,255,0.06)' }}
      }}
    }}
  }}
}});"""


def _kpi_slide_html(slide: SlidePayload) -> str:
    bullets_html = "".join(
        f'<li><span class="bullet-dot"></span>{bp}</li>'
        for bp in slide.bullet_points
    )

    # KPI slides don't have chart_data on SlidePayload (description only) —
    # but the spec says KPI slides use kpi.chart_data from the original SlideInput.
    # Since GeneratePDFRequest.slides is List[SlidePayload] which has no chart_data,
    # we render the left panel only. Chart data is on root cause slides.
    # (If you want to add chart_data to SlidePayload in future, hook it in here.)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px; overflow: hidden;
    background: #0f1117;
    font-family: 'Inter', 'Segoe UI', sans-serif; color: #fff;
    display: flex;
  }}
  .left {{
    width: 100%; padding: 70px 80px;
    display: flex; flex-direction: column; justify-content: center;
  }}
  .kpi-name {{
    font-size: 12px; font-weight: 700; letter-spacing: 2.5px;
    text-transform: uppercase; color: #00d4aa; margin-bottom: 20px;
  }}
  h2 {{ font-size: 36px; font-weight: 800; margin-bottom: 24px; line-height: 1.25; max-width: 700px; }}
  .desc {{ font-size: 16px; color: #a0aec0; line-height: 1.75; margin-bottom: 32px; max-width: 720px; }}
  .bullets {{ list-style: none; display: flex; flex-direction: column; gap: 12px; }}
  .bullets li {{
    display: flex; gap: 12px; align-items: flex-start;
    font-size: 14px; color: #cbd5e0; line-height: 1.5;
  }}
  .bullet-dot {{
    width: 7px; height: 7px; border-radius: 50%;
    background: #00d4aa; margin-top: 6px; flex-shrink: 0;
  }}
  .accent-line {{
    width: 48px; height: 3px;
    background: linear-gradient(90deg, #00d4aa, #0066ff);
    border-radius: 2px; margin-bottom: 28px;
  }}
</style>
</head>
<body>
  <div class="left">
    <div class="kpi-name">{slide.kpi_name}</div>
    <div class="accent-line"></div>
    <h2>{slide.title}</h2>
    <p class="desc">{slide.description}</p>
    <ul class="bullets">{bullets_html}</ul>
  </div>
</body>
</html>"""


def _kpi_chart_slide_html(
    kpi_name: str,
    title: str,
    description: str,
    bullet_points: List[str],
    chart_data,
    breadcrumb: str | None = None,
) -> str:
    bullets_html = "".join(
        f'<li><span class="bullet-dot"></span>{bp}</li>'
        for bp in bullet_points
    )
    breadcrumb_html = (
        f'<div class="breadcrumb">{breadcrumb}</div>' if breadcrumb else ""
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px; overflow: hidden;
    background: #0f1117;
    font-family: 'Inter', 'Segoe UI', sans-serif; color: #fff;
    display: flex;
  }}
  .left {{
    width: 50%; padding: 60px 50px;
    display: flex; flex-direction: column; justify-content: center;
  }}
  .right {{
    width: 50%; padding: 40px;
    display: flex; align-items: center; justify-content: center;
    background: #161b27;
  }}
  .kpi-name {{
    font-size: 12px; font-weight: 700; letter-spacing: 2.5px;
    text-transform: uppercase; color: #00d4aa; margin-bottom: 16px;
  }}
  h2 {{ font-size: 28px; font-weight: 700; margin-bottom: 20px; line-height: 1.3; }}
  .desc {{ font-size: 14px; color: #a0aec0; line-height: 1.7; margin-bottom: 24px; }}
  .bullets {{ list-style: none; display: flex; flex-direction: column; gap: 10px; }}
  .bullets li {{
    display: flex; gap: 10px; align-items: flex-start;
    font-size: 13px; color: #cbd5e0;
  }}
  .bullet-dot {{
    width: 6px; height: 6px; border-radius: 50%;
    background: #00d4aa; margin-top: 5px; flex-shrink: 0;
  }}
  .breadcrumb {{ font-size: 11px; color: #4a5568; margin-bottom: 12px; }}
  canvas {{ max-width: 100%; max-height: 560px; }}
</style>
</head>
<body>
  <div class="left">
    {breadcrumb_html}
    <div class="kpi-name">{kpi_name}</div>
    <h2>{title}</h2>
    <p class="desc">{description}</p>
    <ul class="bullets">{bullets_html}</ul>
  </div>
  <div class="right">
    <canvas id="myChart"></canvas>
  </div>
  <script src="{_CHART_JS_CDN}"></script>
  <script>{_chart_script(chart_data)}</script>
</body>
</html>"""


# ── PDF generation ────────────────────────────────────────────────────────────

async def generate_pdf_from_slides(request: GeneratePDFRequest) -> str:
    """
    Build one HTML page per slide, render via Playwright, merge into one PDF.
    Returns the filename (not full path) of the merged PDF saved under /static/.
    """
    # Build ordered list of (html, has_chart) tuples
    html_pages: List[tuple[str, bool]] = []

    # Slide 0: title
    html_pages.append((_title_html(request), False))

    for slide in request.slides:
        # Check if any root causes have chart_data — if so, render KPI slide
        # with a chart using the first root cause's data as a proxy.
        # If no root causes, render text-only KPI slide.
        rc_with_charts = [rc for rc in slide.root_causes if rc.chart_data is not None]

        if rc_with_charts:
            # KPI summary slide: use first root cause chart as the main chart
            first_rc = rc_with_charts[0]
            html = _kpi_chart_slide_html(
                kpi_name=slide.kpi_name,
                title=slide.title,
                description=slide.description,
                bullet_points=slide.bullet_points,
                chart_data=first_rc.chart_data,
            )
            html_pages.append((html, True))
        else:
            # Text-only KPI slide
            html_pages.append((_kpi_slide_html(slide), False))

        # Root cause slides
        for rc in slide.root_causes:
            if rc.chart_data is None:
                continue
            html = _kpi_chart_slide_html(
                kpi_name=rc.name,
                title=rc.name,
                description=rc.description,
                bullet_points=rc.bullet_points,
                chart_data=rc.chart_data,
                breadcrumb=f"← {slide.kpi_name} / Root Cause",
            )
            html_pages.append((html, True))

    # Render via Playwright
    tmp = tempfile.mkdtemp()
    pdf_files: List[str] = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                for i, (html, has_chart) in enumerate(html_pages):
                    page = await browser.new_page(
                        viewport={"width": 1280, "height": 720},
                        device_scale_factor=2,
                    )
                    try:
                        await page.set_content(html)
                        await page.wait_for_load_state("networkidle")

                        if has_chart:
                            # Poll for window.__chartReady set by Chart.js animation.onComplete.
                            # Falls back after 8s if the flag never arrives.
                            try:
                                await page.wait_for_function(
                                    "() => window.__chartReady === true",
                                    timeout=8000,
                                )
                            except Exception:
                                # Timeout — give one last fixed wait and continue
                                await page.wait_for_timeout(3000)
                        else:
                            # Text/title slides: wait for full paint (fonts, images, CSS)
                            await page.wait_for_timeout(1500)

                        slide_pdf = os.path.join(tmp, f"slide_{i}.pdf")
                        await page.pdf(
                            path=slide_pdf,
                            width="1280px",
                            height="720px",
                            print_background=True,
                            prefer_css_page_size=True,
                        )
                        pdf_files.append(slide_pdf)
                        print(f"  ✅ Slide {i + 1}/{len(html_pages)} rendered")
                    finally:
                        await page.close()
            finally:
                await browser.close()

        # Merge PDFs
        merged_path = os.path.join(tmp, "merged.pdf")
        merger = PdfMerger()
        for pf in pdf_files:
            merger.append(pf)
        merger.write(merged_path)
        merger.close()

        # Save to /static/
        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.pdf"
        dest = static_dir / filename
        shutil.copy(merged_path, str(dest))

        return filename

    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {type(e).__name__}: {e}") from e

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
