"""
PDF slide generation from structured frontend data.
Restores the original blue-gradient design, adapted for the new data models.
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

from financial_models import GeneratePDFRequest, SlidePayload, ChartData


# ── Logo helper ───────────────────────────────────────────────────────────────

def _get_logo_src(logo_url: str | None, use_dash_logo: bool) -> str | None:
    if not use_dash_logo:
        if logo_url:
            return logo_url.strip().strip("`")
        return None
    logo_path = Path("assets/logo.png")
    if logo_path.exists():
        data = base64.b64encode(logo_path.read_bytes()).decode()
        return f"data:image/png;base64,{data}"
    return "https://dashanalytix.com/wp-content/uploads/2023/11/logo-color.png"


def _fmt_value(v: float) -> str:
    """Format a number as $XM / $XK / $X."""
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:,.0f}"


# ── Title slide ───────────────────────────────────────────────────────────────

def _title_html(req: GeneratePDFRequest) -> str:
    logo_src = _get_logo_src(req.logo_url, req.dash_logo)
    custom_logo = bool(req.logo_url and str(req.logo_url).strip())

    if req.dash_logo:
        logo_wrapper = 'width:56px;height:56px;background:white;border-radius:16px;box-shadow:0 25px 50px -12px rgba(59,130,246,0.3);padding:8px;display:flex;align-items:center;justify-content:center;margin-right:16px;'
        logo_img = 'display:block;width:100%;height:100%;object-fit:contain;'
        show_logo = bool(logo_src)
    elif custom_logo:
        logo_wrapper = 'width:80px;height:80px;border-radius:50%;overflow:hidden;background:transparent;margin-right:16px;'
        logo_img = 'display:block;width:100%;height:100%;object-fit:cover;'
        show_logo = True
    else:
        logo_wrapper = logo_img = ''
        show_logo = False

    logo_html = (
        f'<div style="{logo_wrapper}"><img src="{logo_src}" alt="Logo" style="{logo_img}"></div>'
        if show_logo else ''
    )

    company = req.company_name or req.organization_name or 'DashAnalytix'
    org     = req.organization_name or 'ORGANIZATION'
    date    = req.presentation_date or datetime.now().strftime('%B %Y')
    prepared_by = req.prepared_by or 'Analytics Team'
    email   = req.contact_email or ''
    website = req.contact_website or ''
    subtitle = req.report_subtitle or ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
:root {{
  --bg-gradient: linear-gradient(135deg,#061551 0%,#0a4d8f 50%,#0e68b3 100%);
  --accent-gradient: linear-gradient(135deg,#3b82f6 0%,#06b6d4 100%);
  --white: #ffffff;
  --blue-100: #dbeafe; --blue-200: #bfdbfe; --blue-300: #93c5fd;
  --cyan-400: #22d3ee; --cyan-300: #67e8f9;
}}
body {{ margin:0; width:1280px; height:720px; overflow:hidden;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  color:#fff; }}
.container {{ width:1280px; height:720px; background:var(--bg-gradient); position:relative; overflow:hidden; }}
.bg-blob {{ position:absolute; border-radius:50%; filter:blur(64px); }}
.blob-1 {{ top:-10%; right:-5%; width:500px; height:500px; background:#60a5fa; opacity:.15; }}
.blob-2 {{ bottom:-10%; left:-5%; width:450px; height:450px; background:#22d3ee; opacity:.15; }}
.blob-3 {{ top:30%; right:10%; width:300px; height:300px; background:#3b82f6; opacity:.10; }}
.geometric {{ position:absolute; border:2px solid; opacity:.2; }}
.glass {{ background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.1); }}
.badge {{ display:inline-flex; align-items:center; padding:8px 20px; border-radius:9999px; }}
.dot {{ width:8px; height:8px; background:var(--cyan-400); border-radius:50%; margin-right:8px; }}
</style>
</head>
<body>
<div class="container">
  <div class="bg-blob blob-1"></div>
  <div class="bg-blob blob-2"></div>
  <div class="bg-blob blob-3"></div>
  <div class="geometric" style="top:15%;right:20%;width:64px;height:64px;border-color:#60a5fa;transform:rotate(45deg);"></div>
  <div class="geometric" style="bottom:25%;left:15%;width:80px;height:80px;border-color:#22d3ee;transform:rotate(12deg);"></div>

  <!-- Header -->
  <div style="position:absolute;top:0;left:0;right:0;padding:32px 64px;display:flex;justify-content:space-between;align-items:center;z-index:20;">
    <div style="display:flex;align-items:center;">
      {logo_html}
      <div>
        <div style="font-size:24px;font-weight:700;color:white;letter-spacing:-.025em;">{company}</div>
        <div style="font-size:12px;color:var(--blue-300);font-weight:500;letter-spacing:.05em;text-transform:uppercase;">FINANCIAL INTELLIGENCE</div>
      </div>
    </div>
    <div class="glass" style="padding:8px 24px;border-radius:9999px;">
      <span style="color:var(--blue-200);font-weight:600;font-size:14px;">{org}</span>
    </div>
  </div>

  <!-- Main content -->
  <div style="position:relative;height:100%;display:flex;flex-direction:column;justify-content:center;padding:0 64px;z-index:10;">
    <div style="max-width:1024px;">
      <div class="glass badge" style="margin-bottom:32px;">
        <div class="dot"></div>
        <span style="color:var(--cyan-300);font-weight:700;font-size:14px;letter-spacing:.1em;text-transform:uppercase;">Financial Report</span>
      </div>
      <h1 style="font-size:72px;font-weight:900;color:white;line-height:1.1;margin:0 0 32px;letter-spacing:-.025em;">{req.report_title}</h1>
      {"" if not subtitle else f'<div style="display:flex;align-items:center;margin-bottom:40px;"><div style="width:6px;height:64px;background:var(--accent-gradient);border-radius:9999px;margin-right:20px;box-shadow:0 10px 15px -3px rgba(59,130,246,.5);"></div><h2 style="font-size:30px;font-weight:700;color:var(--blue-100);line-height:1.25;margin:0;">{subtitle}</h2></div>'}
      <!-- Metadata row -->
      <div style="display:flex;align-items:center;gap:16px;">
        <div class="glass" style="display:flex;align-items:center;padding:12px 20px;border-radius:12px;">
          <svg style="width:24px;height:24px;color:var(--cyan-400);margin-right:12px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
          <div><div style="font-size:12px;color:var(--blue-300);font-weight:500;">Report Date</div><div style="font-weight:700;color:white;">{date}</div></div>
        </div>
        <div class="glass" style="display:flex;align-items:center;padding:12px 20px;border-radius:12px;">
          <svg style="width:24px;height:24px;color:var(--cyan-400);margin-right:12px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          <div><div style="font-size:12px;color:var(--blue-300);font-weight:500;">Document Type</div><div style="font-weight:700;color:white;">Executive Summary</div></div>
        </div>
        <div class="glass" style="display:flex;align-items:center;padding:12px 20px;border-radius:12px;">
          <svg style="width:24px;height:24px;color:var(--cyan-400);margin-right:12px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
          <div><div style="font-size:12px;color:var(--blue-300);font-weight:500;">Prepared By</div><div style="font-weight:700;color:white;">{prepared_by}</div></div>
        </div>
      </div>
    </div>
  </div>

  <!-- Footer -->
  <div style="position:absolute;bottom:0;left:0;right:0;padding:24px 64px;background:linear-gradient(to right,rgba(0,0,0,.4),rgba(0,0,0,.3),rgba(0,0,0,.4));border-top:1px solid rgba(255,255,255,.1);display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;align-items:center;color:var(--blue-100);font-size:14px;gap:48px;">
      {"" if not email else f'<div style="display:flex;align-items:center;"><svg style="width:16px;height:16px;color:var(--cyan-400);margin-right:8px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg><span style="font-weight:600;">{email}</span></div>'}
      {"" if not website else f'<div style="display:flex;align-items:center;"><svg style="width:16px;height:16px;color:var(--cyan-400);margin-right:8px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/></svg><span style="font-weight:600;">{website}</span></div>'}
    </div>
    <div style="display:flex;align-items:center;">
      <div style="width:8px;height:8px;background:var(--cyan-400);border-radius:50%;margin-right:12px;"></div>
      <span style="font-size:14px;opacity:.7;color:white;">Confidential</span>
    </div>
  </div>
</div>
</body>
</html>"""


# ── KPI / Root-cause chart slide ──────────────────────────────────────────────

_CDN_CHARTJS   = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"
_CDN_DATALABELS = "https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"


def _kpi_chart_slide_html(
    kpi_name: str,
    title: str,
    description: str,
    bullet_points: List[str],
    chart_data: ChartData,
    breadcrumb: str | None = None,
) -> str:
    labels_json = json.dumps(chart_data.labels)
    values_json = json.dumps(chart_data.values)
    chart_type  = chart_data.chart_type
    has_comparison = bool(chart_data.cp_values)

    # Derive a "latest value" to show prominently on left panel
    latest_val  = chart_data.values[-1] if chart_data.values else 0
    latest_label = chart_data.labels[-1] if chart_data.labels else ""
    latest_fmt  = _fmt_value(latest_val)

    cp_values_json = json.dumps(chart_data.cp_values or [])
    cp_label_str   = chart_data.cp_label or "Comparison"
    tp_label_str   = chart_data.tp_label or "Selected"

    bullets_html = "".join([
        f'''<div style="display:flex;align-items:start;background:white;border-radius:8px;padding:12px;
                box-shadow:0 1px 2px rgba(0,0,0,.05);margin-bottom:8px;">
              <div style="flex-shrink:0;width:24px;height:24px;border-radius:8px;
                  background:linear-gradient(135deg,#3b82f6,#2563eb);display:flex;align-items:center;
                  justify-content:center;margin-right:12px;">
                <svg style="width:12px;height:12px;color:white;" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
              <span style="font-size:12px;font-weight:600;color:#374151;padding-top:2px;">{bp}</span>
            </div>'''
        for bp in bullet_points[:4]
    ])

    breadcrumb_html = (
        f'<div style="display:inline-block;padding:4px 12px;background:rgba(96,165,250,.2);'
        f'border-radius:9999px;margin-bottom:8px;border:1px solid rgba(147,197,253,.3);">'
        f'<span style="color:#dbeafe;font-weight:700;font-size:11px;text-transform:uppercase;'
        f'letter-spacing:.08em;">{breadcrumb}</span></div>'
        if breadcrumb else
        '<div style="display:inline-block;padding:6px 16px;background:rgba(96,165,250,.2);'
        'border-radius:9999px;margin-bottom:16px;border:1px solid rgba(147,197,253,.3);">'
        '<span style="color:#dbeafe;font-weight:700;font-size:12px;text-transform:uppercase;'
        'letter-spacing:.1em;">METRIC ANALYSIS</span></div>'
    )

    # Bar chart config for the secondary chart on the right panel
    bar_bg = "'#3b82f6'" if chart_type == "bar" else "'#2563eb'"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="{_CDN_CHARTJS}"></script>
<script src="{_CDN_DATALABELS}"></script>
<style>
  @keyframes slideIn {{ from {{ opacity:0; transform:translateY(20px); }} to {{ opacity:1; transform:translateY(0); }} }}
  @keyframes pulse-glow {{ 0%,100% {{ opacity:1; box-shadow:0 0 20px rgba(96,165,250,.6); }} 50% {{ opacity:.7; box-shadow:0 0 30px rgba(96,165,250,.9); }} }}
</style>
</head>
<body style="margin:0;width:1280px;height:720px;overflow:hidden;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#000;">
<div style="width:1280px;height:720px;background:white;display:flex;position:relative;">

  <!-- LEFT PANEL (dark blue) -->
  <div style="width:50%;background:linear-gradient(135deg,#0a1628 0%,#1e3a8a 50%,#1e40af 100%);
      padding:32px 48px;color:white;position:relative;z-index:10;overflow:hidden;">
    <div style="position:absolute;top:-50%;right:-50%;width:100%;height:100%;
        background:radial-gradient(circle,rgba(96,165,250,.15) 0%,transparent 70%);"></div>
    <div style="position:absolute;bottom:-30%;left:-30%;width:80%;height:80%;
        background:radial-gradient(circle,rgba(147,197,253,.1) 0%,transparent 60%);"></div>

    {breadcrumb_html}
    <h1 style="font-size:34px;font-weight:900;margin-bottom:12px;line-height:1.25;">{kpi_name if not breadcrumb else title}</h1>
    {"" if breadcrumb else f'<p style="font-size:13px;font-weight:500;margin-bottom:10px;color:#dbeafe;">{title}</p>'}
    <p style="font-size:12px;color:#93c5fd;line-height:1.6;margin-bottom:14px;">{description}</p>
    <div style="width:96px;height:4px;background:linear-gradient(to right,#60a5fa,#22d3ee,#3b82f6);
        margin-bottom:20px;border-radius:9999px;"></div>

    <!-- Latest value — solid colour (no gradient-clip) -->
    <div style="font-size:64px;font-weight:900;color:#60a5fa;margin-bottom:8px;
        text-shadow:0 2px 8px rgba(96,165,250,.4);">{latest_fmt}</div>
    <h2 style="font-size:18px;font-weight:700;margin-bottom:24px;color:#f8fafc;">{latest_label}</h2>

    <!-- Mini sparkline -->
    <div style="width:100%;height:110px;background:rgba(255,255,255,.1);
        border:1px solid rgba(255,255,255,.2);border-radius:16px;padding:10px;
        box-shadow:0 8px 32px rgba(0,0,0,.2);margin-bottom:16px;">
      <canvas id="miniChart"></canvas>
    </div>

    <div style="position:absolute;top:32px;right:32px;width:16px;height:16px;
        background:#22d3ee;border-radius:50%;animation:pulse-glow 2s ease-in-out infinite;"></div>
  </div>

  <!-- RIGHT PANEL (light) -->
  <div style="width:50%;background:linear-gradient(to bottom right,#f9fafb,#f3f4f6);padding:28px 36px;position:relative;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
      <h3 style="font-size:18px;font-weight:900;color:#1f2937;margin:0;">Performance Trend</h3>
      <div style="display:flex;align-items:center;gap:8px;background:white;padding:6px 12px;
          border-radius:9999px;box-shadow:0 1px 2px rgba(0,0,0,.05);">
        <div style="width:10px;height:10px;border-radius:50%;background:linear-gradient(to right,#3b82f6,#2563eb);"></div>
        <span style="font-size:12px;font-weight:700;color:#374151;">{kpi_name}</span>
      </div>
    </div>
    <!-- Main chart -->
    <div style="height:200px;background:white;border-radius:16px;padding:16px;
        border:1px solid rgba(0,0,0,.05);box-shadow:0 4px 6px -1px rgba(0,0,0,.05);margin-bottom:12px;">
      <canvas id="myChart"></canvas>
    </div>
    <!-- Secondary bar chart -->
    <div style="height:100px;background:white;border-radius:16px;padding:10px;
        border:1px solid rgba(0,0,0,.05);box-shadow:0 4px 6px -1px rgba(0,0,0,.05);margin-bottom:12px;">
      <canvas id="barChart"></canvas>
    </div>
    <!-- Bullets -->
    <div style="display:flex;flex-direction:column;gap:4px;">
      {bullets_html}
    </div>
  </div>

  <div style="position:absolute;bottom:0;left:0;right:0;height:6px;
      background:linear-gradient(to right,#2563eb,#06b6d4,#2563eb);"></div>
</div>

<script>
window.addEventListener('load', function() {{
  setTimeout(function() {{
    Chart.register(ChartDataLabels);
    Chart.defaults.font.family = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif";

    const labels    = {labels_json};
    const values    = {values_json};
    const cpValues  = {cp_values_json};
    const hasComp   = {('true' if has_comparison else 'false')};
    const cpLabel   = {json.dumps(cp_label_str)};
    const tpLabel   = {json.dumps(tp_label_str)};

    const fmtVal = function(v) {{
      if (Math.abs(v) >= 1000000) return '$'+(v/1000000).toFixed(1)+'M';
      if (Math.abs(v) >= 1000)    return '$'+(v/1000).toFixed(0)+'K';
      return '$'+v.toLocaleString();
    }};

    // Main chart — grouped bar when comparison data present, otherwise single series
    const ctx = document.getElementById('myChart').getContext('2d');
    const mainDatasets = hasComp ? [
      {{
        label: cpLabel,
        data: cpValues,
        backgroundColor: '#93c5fd',
        borderRadius: 4,
        borderSkipped: false,
      }},
      {{
        label: tpLabel,
        data: values,
        backgroundColor: '#2563eb',
        borderRadius: 4,
        borderSkipped: false,
      }}
    ] : [{{
      label: '{kpi_name}',
      data: values,
      borderColor: '#2563eb',
      backgroundColor: '{chart_type}' === 'bar' ? '#2563eb' : 'rgba(37,99,235,.1)',
      borderWidth: 3,
      pointRadius: 5,
      pointBackgroundColor: '#2563eb',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      tension: 0.4,
      fill: '{chart_type}' !== 'bar',
      borderRadius: 4,
    }}];

    new Chart(ctx, {{
      type: hasComp ? 'bar' : '{chart_type}',
      data: {{ labels: labels, datasets: mainDatasets }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        layout: {{ padding: {{ top: 28, right: 10, bottom: 8, left: 8 }} }},
        plugins: {{
          legend: {{ display: hasComp, position: 'top', labels: {{ font: {{ size: 9 }}, boxWidth: 12 }} }},
          datalabels: {{
            display: true, align: 'top', anchor: 'end', offset: 4,
            color: '#1e40af',
            backgroundColor: 'rgba(255,255,255,.95)',
            borderRadius: 4, borderWidth: 1, borderColor: '#3b82f6',
            padding: 3,
            font: {{ size: 9, weight: '800' }},
            formatter: fmtVal,
          }},
          tooltip: {{ backgroundColor: 'rgba(15,23,42,.95)', padding: 10, cornerRadius: 8 }}
        }},
        scales: {{
          y: {{ beginAtZero: true, grace: '15%', ticks: {{ font: {{ size: 9 }}, color: '#64748b' }},
                grid: {{ color: 'rgba(0,0,0,.05)' }}, border: {{ display: false }} }},
          x: {{ ticks: {{ font: {{ size: 9 }}, color: '#64748b' }},
                grid: {{ display: false }}, border: {{ display: false }} }}
        }}
      }}
    }});

    // Secondary bar chart — show comparison side-by-side too, or single series
    const barCtx = document.getElementById('barChart').getContext('2d');
    const barDatasets = hasComp ? [
      {{ label: cpLabel, data: cpValues, backgroundColor: '#93c5fd', borderRadius: 4 }},
      {{ label: tpLabel, data: values,   backgroundColor: {bar_bg},  borderRadius: 4 }}
    ] : [{{ data: values, backgroundColor: {bar_bg}, borderRadius: 4 }}];

    new Chart(barCtx, {{
      type: 'bar',
      data: {{ labels: labels, datasets: barDatasets }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }}, datalabels: {{ display: false }} }},
        scales: {{
          y: {{ display: true, beginAtZero: true, ticks: {{ font: {{ size: 8 }}, color: '#64748b' }},
                grid: {{ display: false }}, border: {{ display: false }} }},
          x: {{ ticks: {{ font: {{ size: 8 }}, color: '#64748b' }},
                grid: {{ display: false }}, border: {{ display: false }} }}
        }}
      }}
    }});

    // Mini sparkline (left panel)
    const miniCtx = document.getElementById('miniChart').getContext('2d');
    new Chart(miniCtx, {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [{{
          data: values,
          borderColor: '#60a5fa',
          backgroundColor: 'rgba(96,165,250,.2)',
          borderWidth: 3, pointRadius: 0, tension: 0.4, fill: true
        }}]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }}, datalabels: {{ display: false }} }},
        scales: {{ y: {{ display: false, beginAtZero: true }}, x: {{ display: false }} }},
        animation: {{ onComplete: function() {{ window.__chartReady = true; }} }}
      }}
    }});
  }}, 500);
}});
</script>
</body>
</html>"""


def _kpi_text_slide_html(slide: SlidePayload) -> str:
    """Text-only KPI slide (when no root causes have chart data)."""
    bullets_html = "".join([
        f'''<div style="display:flex;align-items:start;background:white;border-radius:8px;padding:14px;
                box-shadow:0 1px 2px rgba(0,0,0,.05);margin-bottom:10px;">
              <div style="flex-shrink:0;width:28px;height:28px;border-radius:8px;
                  background:linear-gradient(135deg,#3b82f6,#2563eb);display:flex;align-items:center;
                  justify-content:center;margin-right:14px;">
                <svg style="width:14px;height:14px;color:white;" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
              <span style="font-size:14px;font-weight:600;color:#374151;padding-top:3px;">{bp}</span>
            </div>'''
        for bp in slide.bullet_points[:5]
    ])

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
</head>
<body style="margin:0;width:1280px;height:720px;overflow:hidden;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#000;">
<div style="width:1280px;height:720px;background:white;display:flex;position:relative;">

  <!-- LEFT PANEL -->
  <div style="width:50%;background:linear-gradient(135deg,#0a1628 0%,#1e3a8a 50%,#1e40af 100%);
      padding:40px 56px;color:white;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center;">
    <div style="position:absolute;top:-50%;right:-50%;width:100%;height:100%;
        background:radial-gradient(circle,rgba(96,165,250,.15) 0%,transparent 70%);"></div>

    <div style="display:inline-block;padding:6px 16px;background:rgba(96,165,250,.2);
        border-radius:9999px;margin-bottom:20px;border:1px solid rgba(147,197,253,.3);">
      <span style="color:#dbeafe;font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.1em;">METRIC ANALYSIS</span>
    </div>
    <h1 style="font-size:40px;font-weight:900;margin-bottom:16px;line-height:1.2;">{slide.kpi_name}</h1>
    <div style="width:96px;height:4px;background:linear-gradient(to right,#60a5fa,#22d3ee);margin-bottom:24px;border-radius:9999px;"></div>
    <p style="font-size:16px;color:#dbeafe;line-height:1.65;margin:0;">{slide.description}</p>
  </div>

  <!-- RIGHT PANEL -->
  <div style="width:50%;background:linear-gradient(to bottom right,#f9fafb,#f3f4f6);
      padding:40px 48px;display:flex;flex-direction:column;justify-content:center;">
    <h2 style="font-size:22px;font-weight:900;color:#1f2937;margin-bottom:24px;">{slide.title}</h2>
    {bullets_html}
  </div>

  <div style="position:absolute;bottom:0;left:0;right:0;height:6px;
      background:linear-gradient(to right,#2563eb,#06b6d4,#2563eb);"></div>
</div>
</body>
</html>"""


# ── PDF generation ────────────────────────────────────────────────────────────

async def generate_pdf_from_slides(request: GeneratePDFRequest) -> str:
    """
    Renders all slides to PDF using Playwright and merges them with PyPDF2.
    Returns the filename (not full path) saved under /static/.
    """
    # Build ordered page list: (html, has_chart)
    html_pages: List[tuple[str, bool]] = []

    html_pages.append((_title_html(request), False))

    for slide in request.slides:
        rc_with_charts = [rc for rc in slide.root_causes if rc.chart_data is not None]

        # Prefer the slide's own chart_data; fall back to first root cause's chart
        kpi_chart = slide.chart_data or (rc_with_charts[0].chart_data if rc_with_charts else None)

        if kpi_chart:
            html = _kpi_chart_slide_html(
                kpi_name=slide.kpi_name,
                title=slide.title,
                description=slide.description,
                bullet_points=slide.bullet_points,
                chart_data=kpi_chart,
            )
            html_pages.append((html, True))
        else:
            html_pages.append((_kpi_text_slide_html(slide), False))

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
                            # Wait for Chart.js animation.onComplete to set window.__chartReady
                            try:
                                await page.wait_for_function(
                                    "() => window.__chartReady === true",
                                    timeout=8000,
                                )
                            except Exception:
                                await page.wait_for_timeout(3000)
                        else:
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

        merged_path = os.path.join(tmp, "merged.pdf")
        merger = PdfMerger()
        for pf in pdf_files:
            merger.append(pf)
        merger.write(merged_path)
        merger.close()

        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.pdf"
        shutil.copy(merged_path, str(static_dir / filename))

        return filename

    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {type(e).__name__}: {e}") from e

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

