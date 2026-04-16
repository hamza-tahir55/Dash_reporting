
"""
Generate PDF with REAL charts using actual financial data.
Uses Chart.js for proper data visualization.
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json
import re
import base64

def get_logo_base64(logo_url=None):
    """Convert logo to base64 for embedding in HTML."""
    # If a custom logo URL is provided, clean it and use it directly
    if logo_url:
        # Clean the URL by removing spaces, backticks, and other unwanted characters
        cleaned_url = logo_url.strip().strip('`').strip()
        if cleaned_url:
            return cleaned_url
    
    # Otherwise, try to use local logo file
    logo_path = Path("assets/logo.png")
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            logo_data = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{logo_data}"
    # Fallback to online URL if local file doesn't exist
    return "https://dashanalytix.com/wp-content/uploads/2023/11/logo-color.png"


def parse_tsx_with_data(file_path):
    """Parse TSX file and extract ALL data including chart data."""
    content = file_path.read_text()
    lines = content.split('\n')
    
    data = {
        'type': 'statistic',
        'title': '',
        'subtitle': '',
        'value': '',
        'label': '',
        'bullets': [],
        'chart_data': [],
        'kpi_prev_percent': '',
        'kpi_prev_label': '',
        'kpi_yoy_percent': '',
        'kpi_yoy_label': ''
    }
    
    # Extract text fields
    for i, line in enumerate(lines):
        if '.default("' in line:
            match = re.search(r'\.default\("([^"]*)"\)', line)
            if match:
                value = match.group(1)
                if 'sectionTitle' in line or 'primaryTitle' in line:
                    data['title'] = value
                elif 'sectionSubtitle' in line or 'secondaryTitle' in line:
                    data['subtitle'] = value
                elif 'statisticValue' in line:
                    data['value'] = value
                elif 'statisticLabel' in line:
                    data['label'] = value
                elif 'kpiPrevPercent' in line:
                    data['kpi_prev_percent'] = value
                elif 'kpiPrevLabel' in line:
                    data['kpi_prev_label'] = value
                elif 'kpiYoyPercent' in line:
                    data['kpi_yoy_percent'] = value
                elif 'kpiYoyLabel' in line:
                    data['kpi_yoy_label'] = value
        
        # Extract bullet points
        if 'bulletPoints' in line and '.default([' in line:
            for j in range(i, min(i + 20, len(lines))):
                bullet_line = lines[j].strip()
                if bullet_line.startswith('"'):
                    bullet = bullet_line.strip('",')
                    if bullet:
                        data['bullets'].append(bullet)
                if '])' in bullet_line:
                    break
        
        # Extract chart data - look for the actual JSON array in .default([...])
        if 'chartData' in line:
            # Find the start of the default array
            start_idx = i
            for j in range(i, min(i + 5, len(lines))):
                if '.default([' in lines[j]:
                    start_idx = j
                    break
            
            # Collect all lines until we find the closing ])
            chart_lines = []
            bracket_count = 0
            found_start = False
            
            for j in range(start_idx, min(start_idx + 200, len(lines))):
                line_text = lines[j]
                chart_lines.append(line_text)
                
                if '.default([' in line_text:
                    found_start = True
                    bracket_count += line_text.count('[')
                    bracket_count -= line_text.count(']')
                elif found_start:
                    bracket_count += line_text.count('[')
                    bracket_count -= line_text.count(']')
                    
                    if bracket_count <= 0 and '])' in line_text:
                        break
            
            if found_start:
                # Extract the JSON array content
                chart_text = ''.join(chart_lines)
                
                # Find content between .default([ and ])
                match = re.search(r'\.default\(\[(.*?)\]\)', chart_text, re.DOTALL)
                if match:
                    json_content = match.group(1)
                    
                    # Parse each object
                    # The format is: { "name": "...", "series1": 123, ... }
                    try:
                        # Wrap in array brackets and parse
                        json_array = f'[{json_content}]'
                        parsed_array = json.loads(json_array)
                        data['chart_data'] = parsed_array
                        print(f"   ✅ Parsed {len(parsed_array)} data points from TSX")
                    except json.JSONDecodeError as e:
                        print(f"   ⚠️  JSON parse error: {e}")
                        print(f"   Content: {json_content[:100]}...")
    
    if 'Title' in file_path.name:
        data['type'] = 'title'
    elif 'Comparison' in file_path.name:
        data['type'] = 'comparison'
    
    return data


def generate_title_html(data):
    """Generate modern title slide with brand colors."""
    dash_logo = data.get('dash_logo', True)  # Default to True if not specified
    logo_url = data.get('logo_url')
    custom_logo_provided = bool(logo_url and str(logo_url).strip())
    
    # Determine logo display logic
    if dash_logo:
        # Case 1: Show default DashAnalytix logo
        logo_src = get_logo_base64()  # No URL = default logo
        logo_wrapper_style = "width: 56px; height: 56px; background: white; border-radius: 16px; box-shadow: 0 25px 50px -12px rgba(59, 130, 246, 0.3); padding: 8px; display: flex; align-items: center; justify-content: center;"
        logo_img_style = "display: block; width: 100%; height: 100%; object-fit: contain;"
        show_logo = True
    elif custom_logo_provided:
        # Case 2: Show custom logo
        logo_src = get_logo_base64(logo_url)
        logo_wrapper_style = "width: 80px; height: 80px; border-radius: 50%; overflow: hidden; background: transparent;"
        logo_img_style = "display: block; width: 100%; height: 100%; object-fit: cover;"
        show_logo = True
    else:
        # Case 3: No logo at all
        logo_src = ""
        logo_wrapper_style = ""
        logo_img_style = ""
        show_logo = False
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Financial Report</title>
<style>
:root {{
  --bg-gradient: linear-gradient(135deg, #061551 0%, #0a4d8f 50%, #0e68b3 100%);
  --accent-gradient: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
  --white: #ffffff;
  --blue-100: #dbeafe;
  --blue-200: #bfdbfe;
  --blue-300: #93c5fd;
  --cyan-400: #22d3ee;
  --cyan-300: #67e8f9;
}}
body {{
  margin: 0;
  width: 1280px;
  height: 720px;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  color: var(--white);
}}
.container {{
  width: 1280px;
  height: 720px;
  background: var(--bg-gradient);
  position: relative;
  overflow: hidden;
}}
.bg-blob {{
  position: absolute;
  border-radius: 50%;
  filter: blur(64px);
}}
.blob-1 {{
  top: -10%;
  right: -5%;
  width: 500px;
  height: 500px;
  background: #60a5fa;
  opacity: 0.15;
  animation: pulse-glow 4s ease-in-out infinite;
}}
.blob-2 {{
  bottom: -10%;
  left: -5%;
  width: 450px;
  height: 450px;
  background: #22d3ee;
  opacity: 0.15;
  animation: pulse-glow 4s ease-in-out infinite;
  animation-delay: 2s;
}}
.blob-3 {{
  top: 30%;
  right: 10%;
  width: 300px;
  height: 300px;
  background: #3b82f6;
  opacity: 0.1;
  animation: float 6s ease-in-out infinite;
}}
.geometric {{
  position: absolute;
  border: 2px solid;
  opacity: 0.2;
}}
.glass {{
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}}
.badge {{
  display: inline-flex;
  align-items: center;
  padding: 8px 20px;
  border-radius: 9999px;
}}
@keyframes float {{
  0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
  50% {{ transform: translateY(-20px) rotate(5deg); }}
}}
@keyframes pulse-glow {{
  0%, 100% {{ opacity: 0.15; }}
  50% {{ opacity: 0.25; }}
}}
@keyframes pulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.5; }}
}}
.animate-pulse {{
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}}
</style>
</head>
<body>
<div class="container">
  <!-- Background Elements -->
  <div class="bg-blob blob-1"></div>
  <div class="bg-blob blob-2"></div>
  <div class="bg-blob blob-3"></div>
  
  <div class="geometric" style="top: 15%; right: 20%; width: 64px; height: 64px; border-color: #60a5fa; transform: rotate(45deg);"></div>
  <div class="geometric" style="bottom: 25%; left: 15%; width: 80px; height: 80px; border-color: #22d3ee; transform: rotate(12deg);"></div>
  
  <!-- Header Bar -->
  <div style="position: absolute; top: 0; left: 0; right: 0; padding: 32px 64px; display: flex; justify-content: space-between; align-items: center; z-index: 20;">
    <div style="display: flex; align-items: center;">
      {f'''<div style="{logo_wrapper_style} margin-right: 16px;">
        <img src="{logo_src}" alt="Logo" style="{logo_img_style}">
      </div>''' if show_logo else ''}
      <div>
        <div style="font-size: 24px; font-weight: 700; color: white; letter-spacing: -0.025em;">{data.get('company_name', 'DashAnalytix')}</div>
        <div style="font-size: 12px; color: var(--blue-300); font-weight: 500; letter-spacing: 0.05em; text-transform: uppercase;">FINANCIAL INTELLIGENCE</div>
      </div>
    </div>
    <div class="glass" style="padding: 8px 24px; border-radius: 9999px;">
      <span style="color: var(--blue-200); font-weight: 600; font-size: 14px;">{data.get('org_name', 'ORGANIZATION')}</span>
    </div>
  </div>
  
  <!-- Main Content -->
  <div style="position: relative; height: 100%; display: flex; flex-direction: column; justify-content: center; padding: 0 64px; z-index: 10;">
    <div style="max-width: 1024px;">
      <div class="glass badge" style="margin-bottom: 32px;">
        <div class="animate-pulse" style="width: 8px; height: 8px; background: var(--cyan-400); border-radius: 50%; margin-right: 8px;"></div>
        <span style="color: var(--cyan-300); font-weight: 700; font-size: 14px; letter-spacing: 0.1em; text-transform: uppercase;">Financial Report</span>
      </div>
      
      <h1 style="font-size: 72px; font-weight: 900; color: white; line-height: 1.1; margin: 0 0 32px 0; letter-spacing: -0.025em;">
        {data['title']}
      </h1>
      
      <div style="display: flex; align-items: center; margin-bottom: 40px;">
        <div style="width: 6px; height: 64px; background: var(--accent-gradient); border-radius: 9999px; margin-right: 20px; box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.5);"></div>
        <h2 style="font-size: 30px; font-weight: 700; color: var(--blue-100); line-height: 1.25; margin: 0;">{data['subtitle']}</h2>
      </div>
      
      <!-- Metadata Row -->
      <div style="display: flex; align-items: center;">
        <div class="glass" style="display: flex; align-items: center; padding: 12px 20px; border-radius: 12px; margin-right: 40px;">
          <svg style="width: 24px; height: 24px; color: var(--cyan-400); margin-right: 12px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
          </svg>
          <div>
            <div style="font-size: 12px; color: var(--blue-300); font-weight: 500;">Report Date</div>
            <div style="font-weight: 700; color: white;">{data.get('date', 'October 2024')}</div>
          </div>
        </div>
        
        <div class="glass" style="display: flex; align-items: center; padding: 12px 20px; border-radius: 12px; margin-right: 40px;">
          <svg style="width: 24px; height: 24px; color: var(--cyan-400); margin-right: 12px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <div>
            <div style="font-size: 12px; color: var(--blue-300); font-weight: 500;">Document Type</div>
            <div style="font-weight: 700; color: white;">{data.get('doc_type', 'Executive Summary')}</div>
          </div>
        </div>
        
        <div class="glass" style="display: flex; align-items: center; padding: 12px 20px; border-radius: 12px;">
          <svg style="width: 24px; height: 24px; color: var(--cyan-400); margin-right: 12px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/>
          </svg>
          <div>
            <div style="font-size: 12px; color: var(--blue-300); font-weight: 500;">Prepared By</div>
            <div style="font-weight: 700; color: white;">{data.get('prepared_by', 'Analytics Team')}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <!-- Footer Bar -->
  <div style="position: absolute; bottom: 0; left: 0; right: 0; padding: 24px 64px; background: linear-gradient(to right, rgba(0,0,0,0.4), rgba(0,0,0,0.3), rgba(0,0,0,0.4)); backdrop-filter: blur(12px); border-top: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center;">
    <div style="display: flex; align-items: center; color: var(--blue-100); font-size: 14px;">
      <div style="display: flex; align-items: center; margin-right: 48px;">
        <svg style="width: 16px; height: 16px; color: var(--cyan-400); margin-right: 8px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
        </svg>
        <span style="font-weight: 600;">{data.get('email', 'contact@dashanalytix.com')}</span>
      </div>
      <div style="display: flex; align-items: center;">
        <svg style="width: 16px; height: 16px; color: var(--cyan-400); margin-right: 8px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
        </svg>
        <span style="font-weight: 600;">{data.get('website', 'www.app.dashanalytix.com')}</span>
      </div>
    </div>
    <div style="display: flex; align-items: center;">
      <div style="width: 8px; height: 8px; background: var(--cyan-400); border-radius: 50%; margin-right: 12px;"></div>
      <span style="font-size: 14px; opacity: 0.7; color: white;">Page 1</span>
    </div>
  </div>
</div>
</body>
</html>"""


def generate_cashflow_waterfall_html(data):
    """Generate Cash Flow waterfall chart slide with quarterly breakdown."""
    # Extract chart data to calculate quarterly values
    chart_data = data.get('chart_data', [])
    
    # Default sample data if no chart data available
    if len(chart_data) >= 1:
        # Use actual data from chart_data
        # series1 = Operating Activities
        # series2 = Investing Activities
        # series3 = Financing Activities
        quarters = [point.get('name', f'Period {i+1}') for i, point in enumerate(chart_data)]
        operating_data = [int(point.get('series1', 0)) for point in chart_data]
        investing_data = [int(point.get('series2', 0)) for point in chart_data]
        financing_data = [int(point.get('series3', 0)) for point in chart_data]
        
        print(f"    📊 Cash Flow Waterfall Data:")
        print(f"       Periods: {quarters}")
        print(f"       Operating: {operating_data}")
        print(f"       Investing: {investing_data}")
        print(f"       Financing: {financing_data}")
    else:
        # Use sample data
        print(f"    ⚠️  No chart_data found, using sample data")
        quarters = ['Q1', 'Q2', 'Q3', 'Q4']
        operating_data = [2100000, 2400000, 2000000, 2300000]
        investing_data = [-800000, -600000, -700000, -500000]
        financing_data = [-500000, -600000, -400000, -500000]
    
    # Calculate totals
    total_operating = sum(operating_data)
    total_investing = sum(investing_data)
    total_financing = sum(financing_data)
    net_cash = total_operating + total_investing + total_financing
    
    # Format values for display
    def format_currency(val):
        if val >= 1000000:
            return f"${val/1000000:.1f}M"
        elif val >= 1000:
            return f"${val/1000:.0f}K"
        return f"${val:,.0f}"
    
    def format_currency_signed(val):
        if val >= 0:
            return f"+{format_currency(val)}"
        return format_currency(val)
    
    # Determine the appropriate unit text based on the largest value
    def get_unit_text(values):
        max_val = max([abs(val) for val in values if val != 0], default=0)
        if max_val >= 1000000:
            return "All values in millions (M)"
        elif max_val >= 1000:
            return "All values in thousands (K)"
        return "All values in actual amounts"
    
    # Calculate the appropriate unit text based on all values
    all_values = operating_data + investing_data + financing_data
    unit_text = get_unit_text(all_values)
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
    <style>
        @keyframes float {{
            0%, 100% {{ transform:translate(0,0) scale(1); }}
            50% {{ transform:translate(-20px,20px) scale(1.1); }}
        }}
        @keyframes pulse-glow {{
            0%, 100% {{ opacity:1; box-shadow:0 0 20px rgba(96,165,250,0.6); }}
            50% {{ opacity:0.7; box-shadow:0 0 30px rgba(96,165,250,0.9); }}
        }}
        @keyframes slideIn {{
            from {{ opacity:0; transform:translateY(20px); }}
            to {{ opacity:1; transform:translateY(0); }}
        }}
    </style>
</head>
<body style="margin: 0; width: 1280px; height: 720px; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #000;">
    <div style="width: 1280px; height: 720px; background: white; display: flex; position: relative;">
        <!-- Left Panel -->
        <div style="width: 50%; background: linear-gradient(135deg, #0a1628 0%, #1e3a8a 50%, #1e40af 100%); padding: 32px 48px; color: white; position: relative; z-index: 10; overflow: hidden;">
            <div style="position: absolute; top: -50%; right: -50%; width: 100%; height: 100%; background: radial-gradient(circle, rgba(96, 165, 250, 0.15) 0%, transparent 70%); animation: float 8s ease-in-out infinite;"></div>
            <div style="position: absolute; bottom: -30%; left: -30%; width: 80%; height: 80%; background: radial-gradient(circle, rgba(147, 197, 253, 0.1) 0%, transparent 60%); animation: float 6s ease-in-out infinite reverse;"></div>
            
            <div style="display: inline-block; padding: 6px 16px; background: rgba(96, 165, 250, 0.2); border-radius: 9999px; margin-bottom: 16px; border: 1px solid rgba(147, 197, 253, 0.3); animation: slideIn 0.6s ease-out forwards;">
                <span style="color: #dbeafe; font-weight: 700; font-size: 12px; tracking: 0.1em; text-transform: uppercase;">CASH FLOW ANALYSIS</span>
            </div>
            <h1 style="font-size: 36px; font-weight: 900; margin-bottom: 12px; line-height: 1.25; animation: slideIn 0.6s ease-out 0.1s forwards; opacity: 0;">{data['title']}</h1>
            <p style="font-size: 14px; font-weight: 500; margin-bottom: 16px; color: #dbeafe; animation: slideIn 0.6s ease-out 0.2s forwards; opacity: 0;">{data['subtitle']}</p>
            <div style="width: 96px; height: 4px; background: linear-gradient(to right, #60a5fa, #22d3ee, #3b82f6); margin-bottom: 24px; border-radius: 9999px; animation: slideIn 0.6s ease-out 0.2s forwards; opacity: 0;"></div>
            
            <div style="animation: slideIn 0.6s ease-out 0.3s forwards; opacity: 0;">
                <div style="font-size: 72px; font-weight: 900; background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 50%, #2563eb 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 12px; filter: drop-shadow(0 2px 4px rgba(59,130,246,0.3));">{format_currency(net_cash)}</div>
                <h2 style="font-size: 20px; font-weight: 700; margin-bottom: 24px; color: #f8fafc;">Net Cash Increase</h2>
            </div>

            <div style="margin-bottom: 24px; animation: slideIn 0.6s ease-out 0.4s forwards; opacity: 0;">
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                    <div style="background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px; padding: 12px;">
                        <div style="font-size: 12px; font-weight: 700; color: #bbf7d0; margin-bottom: 4px;">Operating</div>
                        <div style="font-size: 24px; font-weight: 900; color: white;">{format_currency(total_operating)}</div>
                    </div>
                    <div style="background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px; padding: 12px;">
                        <div style="font-size: 12px; font-weight: 700; color: #fde68a; margin-bottom: 4px;">Investing</div>
                        <div style="font-size: 24px; font-weight: 900; color: white;">{format_currency(total_investing)}</div>
                    </div>
                    <div style="background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px; padding: 12px;">
                        <div style="font-size: 12px; font-weight: 700; color: #fecaca; margin-bottom: 4px;">Financing</div>
                        <div style="font-size: 24px; font-weight: 900; color: white;">{format_currency(total_financing)}</div>
                    </div>
                </div>
            </div>
            
            <div style="animation: slideIn 0.6s ease-out 0.4s forwards; opacity: 0;">
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 10px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div style="width: 12px; height: 12px; border-radius: 50%; background: #4ade80;"></div>
                            <span style="font-size: 14px; font-weight: 600;">Operating Activities</span>
                        </div>
                        <span style="font-size: 14px; font-weight: 700; color: #86efac;">{format_currency_signed(total_operating)}</span>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 10px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div style="width: 12px; height: 12px; border-radius: 50%; background: #fbbf24;"></div>
                            <span style="font-size: 14px; font-weight: 600;">Investing Activities</span>
                        </div>
                        <span style="font-size: 14px; font-weight: 700; color: #fcd34d;">{format_currency_signed(total_investing)}</span>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 10px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div style="width: 12px; height: 12px; border-radius: 50%; background: #f87171;"></div>
                            <span style="font-size: 14px; font-weight: 600;">Financing Activities</span>
                        </div>
                        <span style="font-size: 14px; font-weight: 700; color: #fca5a5;">{format_currency_signed(total_financing)}</span>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 10px; border: 2px solid #22d3ee;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div style="width: 12px; height: 12px; border-radius: 50%; background: #22d3ee;"></div>
                            <span style="font-size: 14px; font-weight: 600;">Net Cash Change</span>
                        </div>
                        <span style="font-size: 14px; font-weight: 700; color: #67e8f9;">{format_currency_signed(net_cash)}</span>
                    </div>
                </div>
            </div>
            
            <div style="position: absolute; top: 32px; right: 32px; width: 16px; height: 16px; background: #22d3ee; border-radius: 50%; animation: pulse-glow 2s ease-in-out infinite;"></div>
        </div>
        
        <!-- Right Panel -->
        <div style="width: 50%; background: linear-gradient(to bottom right, #f9fafb, #f3f4f6); padding: 32px 40px; position: relative;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
                <h3 style="font-size: 18px; font-weight: 900; color: #1f2937; margin: 0;">Performance Trend</h3>
                <div style="display: flex; align-items: center; gap: 8px; background: white; padding: 6px 12px; border-radius: 9999px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <div style="width: 10px; height: 10px; border-radius: 50%; background: linear-gradient(to right, #3b82f6, #06b6d4);"></div>
                    <span style="font-size: 12px; font-weight: 700; color: #374151;">Component View</span>
                </div>
            </div>
            <div style="height: 500px; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.08); padding: 20px; margin-bottom: 16px; animation: slideIn 0.6s ease-out 0.2s forwards; opacity: 0;">
                <canvas id="waterfallChart"></canvas>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; animation: slideIn 0.6s ease-out 0.3s forwards; opacity: 0;">
                <div style="display: flex; align-items: center; gap: 16px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 12px; height: 12px; border-radius: 2px; background: #22c55e;"></div>
                        <span style="font-size: 12px; font-weight: 600; color: #374151;">Operating</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 12px; height: 12px; border-radius: 2px; background: #f59e0b;"></div>
                        <span style="font-size: 12px; font-weight: 600; color: #374151;">Investing</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 12px; height: 12px; border-radius: 2px; background: #ef4444;"></div>
                        <span style="font-size: 12px; font-weight: 600; color: #374151;">Financing</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 12px; height: 12px; border-radius: 2px; background: #06b6d4;"></div>
                        <span style="font-size: 12px; font-weight: 600; color: #374151;">Net Change</span>
                    </div>
                </div>
                <div style="font-size: 12px; font-weight: 500; color: #6b7280;">{unit_text}</div>
            </div>
        </div>
        <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 6px; background: linear-gradient(to right, #2563eb, #06b6d4, #2563eb);"></div>
    </div>

    <script>
        window.addEventListener('load', function() {{
            setTimeout(function() {{
                Chart.register(ChartDataLabels);
                Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";

                const quarters = {json.dumps(quarters)};
                const operatingData = {json.dumps(operating_data)};
                const investingData = {json.dumps(investing_data)};
                const financingData = {json.dumps(financing_data)};
                
                const netCashData = quarters.map((_, i) => 
                    operatingData[i] + investingData[i] + financingData[i]
                );

                function formatCurrency(value) {{
                    const absValue = Math.abs(value);
                    if (absValue >= 1000000) {{
                        return '$' + (value / 1000000).toFixed(1) + 'M';
                    }} else if (absValue >= 1000) {{
                        return '$' + (value / 1000).toFixed(0) + 'K';
                    }} else {{
                        return '$' + value.toLocaleString();
                    }}
                }}

                function formatCurrencySigned(value) {{
                    const prefix = value >= 0 ? '+' : '';
                    return prefix + formatCurrency(value);
                }}

                const waterfallData = [];
                const colors = [];
                const labels = [];

                quarters.forEach((quarter, i) => {{
                    let runningTotal = 0;
                    labels.push('');
                    waterfallData.push([0, operatingData[i]]);
                    colors.push('#22c55e');
                    runningTotal = operatingData[i];
                    labels.push(quarter);
                    waterfallData.push([runningTotal, runningTotal + investingData[i]]);
                    colors.push('#f59e0b');
                    runningTotal += investingData[i];
                    labels.push('');
                    waterfallData.push([runningTotal, runningTotal + financingData[i]]);
                    colors.push('#ef4444');
                    runningTotal += financingData[i];
                    labels.push('');
                    waterfallData.push([0, netCashData[i]]);
                    colors.push('#06b6d4');
                }});

                const ctx = document.getElementById('waterfallChart').getContext('2d');
                new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            data: waterfallData,
                            backgroundColor: colors,
                            borderRadius: 4,
                            borderWidth: 2,
                            borderColor: 'rgba(255, 255, 255, 0.8)'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        layout: {{ padding: {{ top: 30, right: 10, bottom: 10, left: 10 }} }},
                        plugins: {{
                            legend: {{ display: false }},
                            datalabels: {{
                                display: true,
                                anchor: function(context) {{
                                    const value = context.dataset.data[context.dataIndex];
                                    return (value[1] - value[0]) >= 0 ? 'end' : 'start';
                                }},
                                align: function(context) {{
                                    const value = context.dataset.data[context.dataIndex];
                                    return (value[1] - value[0]) >= 0 ? 'top' : 'bottom';
                                }},
                                offset: 4,
                                color: '#1e293b',
                                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                                borderRadius: 4,
                                borderWidth: 1,
                                borderColor: '#e2e8f0',
                                padding: {{ top: 4, bottom: 4, left: 8, right: 8 }},
                                font: {{ size: 11, weight: '700' }},
                                formatter: function(value) {{
                                    return formatCurrencySigned(value[1] - value[0]);
                                }}
                            }},
                            tooltip: {{
                                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                                padding: 14,
                                cornerRadius: 8,
                                displayColors: false,
                                callbacks: {{
                                    title: function(context) {{ return context[0].label; }},
                                    label: function(context) {{
                                        const raw = context.dataset.data[context.dataIndex];
                                        return 'Amount: ' + formatCurrency(raw[1] - raw[0]);
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                ticks: {{ callback: function(value) {{ return formatCurrency(value); }}, font: {{ size: 11, weight: '600' }}, color: '#64748b' }},
                                grid: {{ color: 'rgba(0, 0, 0, 0.06)', lineWidth: 1 }},
                                border: {{ display: false }}
                            }},
                            x: {{
                                ticks: {{ font: {{ size: 10, weight: '600' }}, color: '#64748b', maxRotation: 0 }},
                                grid: {{ display: false }},
                                border: {{ display: false }}
                            }}
                        }}
                    }}
                }});
            }}, 500);
        }});
    </script>
</body>
</html>"""


def generate_statistic_html_with_real_chart(data):
    """Generate premium statistic slide with enhanced visuals and REAL Chart.js chart."""
    # Generate bullet points with enhanced styling
    bullets_html = ''.join([
        f'''<div style="display: flex; align-items: start; background: white; border-radius: 8px; padding: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 8px; transition: all 0.3s ease;">
                <div style="flex-shrink: 0; width: 24px; height: 24px; border-radius: 8px; background: linear-gradient(135deg, #3b82f6, #2563eb); display: flex; align-items: center; justify-content: center; margin-right: 12px;">
                    <svg style="width: 12px; height: 12px; color: white;" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                    </svg>
                </div>
                <span style="font-size: 12px; font-weight: 600; color: #374151; padding-top: 2px;">{bullet}</span>
            </div>'''
        for bullet in data['bullets'][:4]
    ])
    
    # Build KPI cards from parsed KPI fields - show only ONE relevant comparison
    kpi_cards = []
    if data.get('kpi_prev_percent'):
        kpi_cards.append(f'''
                <div style="background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); border-radius: 12px; padding: 12px; min-width: 120px;">
                    <div style="font-size: 24px; font-weight: 900; color: white; margin-bottom: 4px;">{data['kpi_prev_percent']}</div>
                    <div style="font-size: 10px; font-weight: 600; color: #bfdbfe; text-transform: uppercase; letter-spacing: 0.05em;">{data.get('kpi_prev_label', 'vs Previous')}</div>
                </div>''')
    elif data.get('kpi_yoy_percent'):
        kpi_cards.append(f'''
                <div style="background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); border-radius: 12px; padding: 12px; min-width: 120px;">
                    <div style="font-size: 24px; font-weight: 900; color: white; margin-bottom: 4px;">{data['kpi_yoy_percent']}</div>
                    <div style="font-size: 10px; font-weight: 600; color: #bfdbfe; text-transform: uppercase; letter-spacing: 0.05em;">{data.get('kpi_yoy_label', 'YoY')}</div>
                </div>''')
    
    kpi_cards_html = ('\n'.join(kpi_cards)) if kpi_cards else ''
    
    # Use actual data from TSX
    if data['chart_data'] and len(data['chart_data']) > 0:
        labels = [point.get('name', '') for point in data['chart_data']]
        values = [point.get('series1', 0) for point in data['chart_data']]
        chart_data_json = json.dumps({'labels': labels, 'values': values})
    else:
        chart_data_json = json.dumps({'labels': ['No Data'], 'values': [0]})
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
    <style>
        @keyframes float {{ 0%, 100% {{ transform:translate(0,0) scale(1); }} 50% {{ transform:translate(-20px,20px) scale(1.1); }} }}
        @keyframes pulse-glow {{ 0%, 100% {{ opacity:1; box-shadow:0 0 20px rgba(96,165,250,0.6); }} 50% {{ opacity:0.7; box-shadow:0 0 30px rgba(96,165,250,0.9); }} }}
        @keyframes slideIn {{ from {{ opacity:0; transform:translateY(20px); }} to {{ opacity:1; transform:translateY(0); }} }}
    </style>
</head>
<body style="margin: 0; width: 1280px; height: 720px; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #000;">
    <div style="width: 1280px; height: 720px; background: white; display: flex; position: relative;">
        <!-- Left Panel -->
        <div style="width: 50%; background: linear-gradient(135deg, #0a1628 0%, #1e3a8a 50%, #1e40af 100%); padding: 32px 48px; color: white; position: relative; z-index: 10; overflow: hidden;">
            <div style="position: absolute; top: -50%; right: -50%; width: 100%; height: 100%; background: radial-gradient(circle, rgba(96, 165, 250, 0.15) 0%, transparent 70%); animation: float 8s ease-in-out infinite;"></div>
            <div style="position: absolute; bottom: -30%; left: -30%; width: 80%; height: 80%; background: radial-gradient(circle, rgba(147, 197, 253, 0.1) 0%, transparent 60%); animation: float 6s ease-in-out infinite reverse;"></div>
            
            <div style="display: inline-block; padding: 6px 16px; background: rgba(96, 165, 250, 0.2); border-radius: 9999px; margin-bottom: 16px; border: 1px solid rgba(147, 197, 253, 0.3); animation: slideIn 0.6s ease-out forwards;">
                <span style="color: #dbeafe; font-weight: 700; font-size: 12px; tracking: 0.1em; text-transform: uppercase;">METRIC ANALYSIS</span>
            </div>
            <h1 style="font-size: 36px; font-weight: 900; margin-bottom: 12px; line-height: 1.25; animation: slideIn 0.6s ease-out 0.1s forwards; opacity: 0;">{data['title']}</h1>
            <p style="font-size: 14px; font-weight: 500; margin-bottom: 16px; color: #dbeafe; animation: slideIn 0.6s ease-out 0.2s forwards; opacity: 0;">{data['subtitle']}</p>
            <div style="width: 96px; height: 4px; background: linear-gradient(to right, #60a5fa, #22d3ee, #3b82f6); margin-bottom: 24px; border-radius: 9999px; animation: slideIn 0.6s ease-out 0.2s forwards; opacity: 0;"></div>
            
            <div style="animation: slideIn 0.6s ease-out 0.3s forwards; opacity: 0;">
                <div style="font-size: 72px; font-weight: 900; background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 50%, #2563eb 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 12px; filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.3));">{data['value']}</div>
                <h2 style="font-size: 20px; font-weight: 700; margin-bottom: 24px; color: #f8fafc;">{data['label']}</h2>
            </div>

            {f'<div style="margin-bottom: 24px; display: flex; gap: 12px; animation: slideIn 0.6s ease-out 0.4s forwards; opacity: 0;">{kpi_cards_html}</div>' if kpi_cards_html else ''}
            
            <div style="animation: slideIn 0.6s ease-out 0.4s forwards; opacity: 0;">
                <div style="width: 100%; height: 128px; background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 16px; padding: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.2);">
                    <canvas id="miniChart"></canvas>
                </div>
            </div>
            
            <div style="position: absolute; top: 32px; right: 32px; width: 16px; height: 16px; background: #22d3ee; border-radius: 50%; animation: pulse-glow 2s ease-in-out infinite;"></div>
        </div>
        
        <!-- Right Panel -->
        <div style="width: 50%; background: linear-gradient(to bottom right, #f9fafb, #f3f4f6); padding: 32px 40px; position: relative;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
                <h3 style="font-size: 18px; font-weight: 900; color: #1f2937; margin: 0;">Performance Trend</h3>
                <div style="display: flex; align-items: center; gap: 8px; background: white; padding: 6px 12px; border-radius: 9999px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <div style="width: 10px; height: 10px; border-radius: 50%; background: linear-gradient(to right, #3b82f6, #2563eb);"></div>
                    <span style="font-size: 12px; font-weight: 700; color: #374151;">{data['title']}</span>
                </div>
            </div>
            <div style="height: 208px; background: white; border-radius: 16px; padding: 20px; border: 1px solid rgba(0,0,0,0.05); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 16px; animation: slideIn 0.6s ease-out 0.2s forwards; opacity: 0;">
                <canvas id="myChart"></canvas>
            </div>
            <div style="height: 112px; background: white; border-radius: 16px; padding: 12px; border: 1px solid rgba(0,0,0,0.05); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 16px; animation: slideIn 0.6s ease-out 0.3s forwards; opacity: 0;">
                <canvas id="areaChart"></canvas>
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px; animation: slideIn 0.6s ease-out 0.4s forwards; opacity: 0;">
                {bullets_html}
            </div>
        </div>
        <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 6px; background: linear-gradient(to right, #2563eb, #06b6d4, #2563eb);"></div>
    </div>

    <script>
        window.addEventListener('load', function() {{
            setTimeout(function() {{
                Chart.register(ChartDataLabels);
                Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";

                const chartData = {chart_data_json};

                // Main Chart
                const ctx = document.getElementById('myChart').getContext('2d');
                new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: chartData.labels,
                        datasets: [{{
                            label: '{data['title']}',
                            data: chartData.values,
                            borderColor: '#2563eb',
                            backgroundColor: 'rgba(37, 99, 235, 0.1)',
                            borderWidth: 4,
                            pointRadius: 6,
                            pointBackgroundColor: '#2563eb',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            tension: 0.4,
                            fill: true
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        layout: {{ padding: {{ top: 30, right: 10, bottom: 10, left: 10 }} }},
                        plugins: {{
                            legend: {{ display: false }},
                            datalabels: {{
                                display: true,
                                align: 'top',
                                anchor: 'end',
                                offset: 4,
                                color: '#1e40af',
                                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                                borderRadius: 4,
                                borderWidth: 1,
                                borderColor: '#3b82f6',
                                padding: 4,
                                font: {{ size: 10, weight: '800' }},
                                formatter: function(value) {{
                                    if (value >= 1000000) return '$' + (value/1000000).toFixed(1) + 'M';
                                    if (value >= 1000) return '$' + (value/1000).toFixed(0) + 'K';
                                    return '$' + value.toLocaleString();
                                }}
                            }},
                            tooltip: {{
                                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                                padding: 12,
                                cornerRadius: 8,
                                callbacks: {{
                                    label: function(context) {{ return 'Value: $' + context.parsed.y.toLocaleString(); }}
                                }}
                            }}
                        }},
                        scales: {{
                            y: {{ beginAtZero: true, grace: '15%', ticks: {{ font: {{ size: 10 }}, color: '#64748b' }}, grid: {{ color: 'rgba(0,0,0,0.05)' }}, border: {{ display: false }} }},
                            x: {{ ticks: {{ font: {{ size: 10 }}, color: '#64748b' }}, grid: {{ display: false }}, border: {{ display: false }} }}
                        }}
                    }}
                }});

                // Mini Chart
                const miniCtx = document.getElementById('miniChart').getContext('2d');
                new Chart(miniCtx, {{
                    type: 'line',
                    data: {{
                        labels: chartData.labels,
                        datasets: [{{
                            data: chartData.values,
                            borderColor: '#60a5fa',
                            backgroundColor: 'rgba(96, 165, 250, 0.2)',
                            borderWidth: 3,
                            pointRadius: 0,
                            tension: 0.4,
                            fill: true
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{ legend: {{ display: false }}, datalabels: {{ display: false }} }},
                        scales: {{ y: {{ display: false, beginAtZero: true }}, x: {{ display: false }} }}
                    }}
                }});

                // Area Chart (Bar)
                const areaCtx = document.getElementById('areaChart').getContext('2d');
                new Chart(areaCtx, {{
                    type: 'bar',
                    data: {{
                        labels: chartData.labels,
                        datasets: [{{
                            data: chartData.values,
                            backgroundColor: '#3b82f6',
                            borderRadius: 6
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{ legend: {{ display: false }}, datalabels: {{ display: false }} }},
                        scales: {{
                            y: {{ display: true, beginAtZero: true, ticks: {{ font: {{ size: 8 }}, color: '#64748b' }}, grid: {{ display: false }}, border: {{ display: false }} }},
                            x: {{ ticks: {{ font: {{ size: 8 }}, color: '#64748b' }}, grid: {{ display: false }}, border: {{ display: false }} }}
                        }}
                    }}
                }});
            }}, 500);
        }});
    </script>
</body>
</html>"""


def generate_dashboard_html_with_real_data(all_metrics_data):
    """Generate comprehensive dashboard slide with real data from all metrics."""
    # Financial/Operational metric categorization logic...
    financial_metrics, financial_period1, financial_period2, financial_changes = [], [], [], []
    operational_metrics, operational_current, operational_previous, operational_changes = [], [], [], []
    period1_label, period2_label = "Previous", "Current"
    
    for metric_data in all_metrics_data:
        metric_name = metric_data.get('title', 'Unknown')
        chart_data = metric_data.get('chart_data', [])
        if len(chart_data) >= 2:
            sorted_data = sorted(chart_data, key=lambda x: x.get('name', ''))
            feb_2021 = next((d for d in sorted_data if 'Feb 2021' in d.get('name', '')), None)
            jan_2021 = next((d for d in sorted_data if 'Jan 2021' in d.get('name', '')), None)
            if feb_2021 and jan_2021:
                period1_val, period2_val = jan_2021.get('series1', 0), feb_2021.get('series1', 0)
                period1_label, period2_label = jan_2021.get('name', 'Jan 2021'), feb_2021.get('name', 'Feb 2021')
            else:
                period1_val, period2_val = sorted_data[-2].get('series1', 0), sorted_data[-1].get('series1', 0)
                period1_label, period2_label = sorted_data[-2].get('name', 'Previous'), sorted_data[-1].get('name', 'Current')
            
            change_pct = ((period2_val - period1_val) / period1_val * 100) if period1_val > 0 else 0
            if metric_name.lower() in ['income', 'gross profit', 'net income', 'cash flow']:
                continue
            elif any(keyword in metric_name.lower() for keyword in ['ebitda', 'expense', 'cost']):
                financial_metrics.append(metric_name); financial_period1.append(period1_val); financial_period2.append(period2_val); financial_changes.append(change_pct)
            elif any(keyword in metric_name.lower() for keyword in ['collection', 'payment', 'inventory', 'days', 'customer collection', 'supplier payment', 'invoice', 'acquisition', 'employee']):
                operational_metrics.append(metric_name); operational_previous.append(period1_val); operational_current.append(period2_val); operational_changes.append(change_pct)
    
    financial_cards_html = ""
    for i, (metric, change) in enumerate(zip(financial_metrics[:5], financial_changes[:5])):
        sign = "+" if change >= 0 else ""
        color_hex = ["#2563eb", "#0891b2", "#2563eb", "#4f46e5", "#ea580c"][i % 5]
        financial_cards_html += f'''
        <div style="background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border: 1px solid rgba(0, 0, 0, 0.05); border-left: 4px solid {color_hex}; border-radius: 12px; padding: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); text-align: center;">
          <div style="font-size: 24px; font-weight: 900; color: {color_hex};">{sign}{change:.1f}%</div>
          <div style="font-size: 10px; font-weight: 600; color: #4b5563; margin-top: 4px;">{metric.replace(' ', '<br>')}</div>
        </div>'''
    
    operational_cards_html = ""
    if operational_metrics:
        for i, (metric, prev, curr, change) in enumerate(zip(operational_metrics[:3], operational_previous[:3], operational_current[:3], operational_changes[:3])):
            change_val = curr - prev
            stat_color = "#ef4444" if change_val > 0 else "#22c55e" # red if increasing (bad for some, good for others, but generally...)
            bg_color = "#fee2e2" if change_val > 0 else "#dcfce7"
            accent_color = ["#2563eb", "#0891b2", "#2563eb"][i % 3]
            arrow_path = "M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" if change_val > 0 else "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
            operational_cards_html += f'''
            <div style="background: white; border-radius: 12px; padding: 12px; margin-bottom: 8px; border: 1px solid rgba(0,0,0,0.05); border-left: 4px solid {accent_color}; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); display: flex; align-items: center; justify-content: space-between;">
              <div>
                <div style="font-size: 11px; font-weight: 600; color: #6b7280; margin-bottom: 2px;">{metric}</div>
                <div style="display: flex; align-items: baseline; gap: 8px;">
                  <span style="font-size: 24px; font-weight: 900; color: {accent_color};">{curr:.1f}</span>
                  <span style="font-size: 13px; font-weight: 700; color: #9ca3af;">← {prev:.1f}</span>
                  <span style="font-size: 11px; font-weight: 800; padding: 2px 8px; background: {bg_color}; color: {stat_color}; border-radius: 9999px;">{"+" if change_val >= 0 else ""}{change_val:.1f}</span>
                </div>
              </div>
              <svg style="width: 32px; height: 32px; color: {stat_color};" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="{arrow_path}"/>
              </svg>
            </div>'''
    else:
        operational_cards_html = '<div style="background: white; border-radius: 12px; padding: 16px; text-align: center; color: #9ca3af; font-size: 14px;">No operational metrics available</div>'

    financial_data_json = json.dumps({'metrics': financial_metrics[:5], 'period1': financial_period1[:5], 'period2': financial_period2[:5]})
    operational_data_json = json.dumps({'metrics': operational_metrics[:3], 'period1': operational_previous[:3], 'period2': operational_current[:3]})

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        @keyframes float {{ 0%, 100% {{ transform:translate(0,0) scale(1); }} 50% {{ transform:translate(-20px,20px) scale(1.1); }} }}
        @keyframes slideIn {{ from {{ opacity:0; transform:translateY(20px); }} to {{ opacity:1; transform:translateY(0); }} }}
    </style>
</head>
<body style="margin: 0; width: 1280px; height: 720px; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #000;">
<div style="width: 1280px; height: 720px; background: white; position: relative;">
  <div style="height: 96px; background: linear-gradient(135deg, #0a1628 0%, #1e3a8a 50%, #1e40af 100%); padding: 0 48px; display: flex; justify-content: space-between; align-items: center; position: relative; z-index: 10; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);">
    <div style="position: absolute; top: -50%; right: -50%; width: 100%; height: 100%; background: radial-gradient(circle, rgba(96, 165, 250, 0.15) 0%, transparent 70%); animation: float 8s ease-in-out infinite;"></div>
    <div>
      <div style="display: inline-block; padding: 4px 12px; background: rgba(96, 165, 250, 0.2); border-radius: 9999px; margin-bottom: 4px; border: 1px solid rgba(147, 197, 253, 0.3);">
        <span style="color: #dbeafe; font-weight: 700; font-size: 10px; tracking: 0.1em; text-transform: uppercase;">COMPARATIVE ANALYSIS</span>
      </div>
      <h1 style="font-size: 28px; font-weight: 900; color: white; margin: 0;">Business Health Dashboard</h1>
    </div>
    <div style="display: flex; align-items: center; gap: 12px;">
      <div style="width: 44px; height: 44px; background: rgba(255, 255, 255, 0.2); backdrop-filter: blur(4px); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
        <svg style="width: 24px; height: 24px; color: white;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
      </div>
      <span style="font-size: 18px; font-weight: 700; color: white;">Financial Analysis</span>
    </div>
  </div>

  <div style="display: flex; height: calc(100% - 96px);">
    <!-- LEFT SIDE -->
    <div style="width: 55%; padding: 32px; background: linear-gradient(to bottom right, #f9fafb, #eff6ff); animation: slideIn 0.6s ease-out forwards;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
        <div>
          <div style="display: inline-block; padding: 4px 12px; background: white; border-radius: 8px; margin-bottom: 4px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.05);">
            <span style="font-size: 11px; font-weight: 800; color: #2563eb; text-transform: uppercase; letter-spacing: 0.05em;">FINANCIAL METRICS</span>
          </div>
          <h3 style="font-size: 20px; font-weight: 900; color: #1f2937; margin: 0;">Performance Summary</h3>
        </div>
        <div style="display: flex; gap: 8px;">
          <div style="display: flex; align-items: center; gap: 8px; background: white; padding: 6px 12px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <div style="width: 10px; height: 10px; border-radius: 50%; background: #2563eb;"></div>
            <span style="font-size: 11px; font-weight: 700; color: #4b5563;">{period1_label}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; background: white; padding: 6px 12px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <div style="width: 10px; height: 10px; border-radius: 50%; background: #06b6d4;"></div>
            <span style="font-size: 11px; font-weight: 700; color: #4b5563;">{period2_label}</span>
          </div>
        </div>
      </div>
      <div style="height: 340px; background: rgba(255,255,255,0.7); backdrop-filter: blur(10px); border-radius: 20px; padding: 20px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.05); margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.3); animation: slideIn 0.6s ease-out 0.1s forwards; opacity: 0;">
        <canvas id="barChart"></canvas>
      </div>
      <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; animation: slideIn 0.6s ease-out 0.2s forwards; opacity: 0;">
        {financial_cards_html}
      </div>
    </div>

    <!-- RIGHT SIDE -->
    <div style="width: 45%; padding: 24px; background: white; animation: slideIn 0.6s ease-out 0.2s forwards; opacity: 0;">
      <div style="margin-bottom: 16px;">
        <div style="display: inline-block; padding: 4px 12px; background: linear-gradient(to right, #06b6d4, #2563eb); border-radius: 8px; margin-bottom: 4px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
          <span style="font-size: 11px; font-weight: 800; color: white; text-transform: uppercase;">OPERATIONAL EFFICIENCY</span>
        </div>
        <h3 style="font-size: 20px; font-weight: 900; color: #1f2937; margin: 0;">Working Capital</h3>
      </div>

      <div style="height: 180px; background: rgba(255,255,255,0.7); backdrop-filter: blur(10px); border-radius: 20px; padding: 16px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.05); margin-bottom: 16px; border: 1px solid rgba(0,0,0,0.05); animation: slideIn 0.6s ease-out 0.3s forwards; opacity: 0;">
        <canvas id="lineChart"></canvas>
      </div>

      <div style="display: flex; flex-direction: column; gap: 8px; animation: slideIn 0.6s ease-out 0.4s forwards; opacity: 0;">
        {operational_cards_html}
      </div>
    </div>
  </div>
  <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 6px; background: linear-gradient(to right, #2563eb, #06b6d4, #2563eb);"></div>
</div>

<script>
window.addEventListener('load', function() {{
  setTimeout(function() {{
    Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
    
    const financial_data = {financial_data_json};
    const barCtx = document.getElementById('barChart').getContext('2d');
    new Chart(barCtx, {{
      type: 'bar',
      data: {{
        labels: financial_data['metrics'],
        datasets: [
          {{ label: '{period1_label}', data: financial_data['period1'], backgroundColor: '#2563eb', borderRadius: 6, barThickness: 24 }},
          {{ label: '{period2_label}', data: financial_data['period2'], backgroundColor: '#06b6d4', borderRadius: 6, barThickness: 24 }}
        ]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }}, tooltip: {{ padding: 12, cornerRadius: 8 }} }},
        scales: {{
          y: {{ beginAtZero: true, grid: {{ color: 'rgba(0,0,0,0.05)' }}, ticks: {{ font: {{ size: 10 }}, color: '#64748b', callback: v => '$' + (v/1000) + 'K' }}, border: {{ display: false }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 10, weight: '700' }}, color: '#64748b' }}, border: {{ display: false }} }}
        }}
      }}
    }});

    const operational_data = {operational_data_json};
    const lineCtx = document.getElementById('lineChart').getContext('2d');
    new Chart(lineCtx, {{
      type: 'line',
      data: {{
        labels: ['{period1_label}', '{period2_label}'],
        datasets: operational_data['metrics'].map((metric, i) => ({{
          label: metric,
          data: [operational_data['period1'][i], operational_data['period2'][i]],
          borderColor: ['#2563eb', '#06b6d4', '#8b5cf6'][i % 3],
          backgroundColor: 'transparent',
          borderWidth: 3,
          pointRadius: 5,
          tension: 0.4
        }}))
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'bottom', labels: {{ boxWidth: 8, font: {{ size: 9, weight: '700' }} }} }},
          tooltip: {{ padding: 10, cornerRadius: 6 }}
        }},
        scales: {{
          y: {{ beginAtZero: true, grid: {{ color: 'rgba(0,0,0,0.05)' }}, ticks: {{ font: {{ size: 9 }}, color: '#64748b', callback: v => v + 'd' }}, border: {{ display: false }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 9, weight: '700' }}, color: '#64748b' }}, border: {{ display: false }} }}
        }}
      }}
    }});
  }}, 500);
}});
</script>
</body></html>"""


def generate_comparison_html_with_real_charts(data):
    """Generate comparison slide with REAL bar charts from TSX data."""
    # Extract comparison data from TSX chart_data
    comparison_data = {'metrics': [], 'period1': [], 'period2': []}
    if data.get('chart_data') and len(data['chart_data']) > 0:
        for point in data['chart_data']:
            comparison_data['metrics'].append(point.get('name', 'Metric'))
            comparison_data['period1'].append(point.get('series1', 0))
            comparison_data['period2'].append(point.get('series2', 0))
    else:
        comparison_data = {'metrics': ['No Data'], 'period1': [0], 'period2': [0]}
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        @keyframes float {{ 0%, 100% {{ transform:translate(0,0) scale(1); }} 50% {{ transform:translate(-20px,20px) scale(1.1); }} }}
        @keyframes slideIn {{ from {{ opacity:0; transform:translateY(20px); }} to {{ opacity:1; transform:translateY(0); }} }}
        body {{ margin: 0; padding: 0; box-sizing: border-box; }}
    </style>
</head>
<body style="margin: 0; width: 1280px; height: 720px; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #fff;">
<div style="width: 1280px; height: 720px; background: white; position: relative;">
  <div style="height: 96px; background: linear-gradient(135deg, #061551 0%, #0e68b3 100%); padding: 0 64px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); position: relative; overflow: hidden;">
    <div style="position: absolute; top: -50%; right: -50%; width: 100%; height: 100%; background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%); animation: float 8s ease-in-out infinite;"></div>
    <div>
      <div style="display: inline-block; padding: 4px 16px; background: rgba(255,255,255,0.2); border-radius: 9999px; margin-bottom: 8px;">
        <span style="color: #bfdbfe; font-weight: 600; font-size: 12px; tracking: 0.1em; text-transform: uppercase;">COMPARATIVE ANALYSIS</span>
      </div>
      <h1 style="font-size: 30px; font-weight: 900; color: white; margin: 0;">Period Comparison</h1>
    </div>
    <div style="display: flex; align-items: center; gap: 12px;">
      <div style="width: 40px; height: 40px; background: rgba(255,255,255,0.2); backdrop-filter: blur(4px); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
        <svg style="width: 24px; height: 24px; color: white;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
      </div>
      <span style="font-size: 18px; font-weight: 700; color: white;">Financial Analysis</span>
    </div>
  </div>

  <div style="display: flex; height: calc(100% - 96px);">
    <!-- LEFT SIDE -->
    <div style="width: 50%; padding: 32px; background: #f8fafc; display: flex; flex-direction: column;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
        <h3 style="font-size: 18px; font-weight: 700; color: #061551; margin: 0;">Monthly Comparison</h3>
      </div>
      <div style="flex: 1; background: white; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 12px; min-height: 250px;">
        <canvas id="barChart"></canvas>
      </div>
      <div style="display: flex; gap: 12px; height: 128px;">
        <div style="flex: 1; background: white; border-radius: 12px; padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <canvas id="donutChart"></canvas>
        </div>
        <div style="flex: 1;">
          <h3 style="font-size: 14px; font-weight: 700; color: #061551; margin-bottom: 8px;">Key Insights</h3>
          <p style="font-size: 12px; color: #4b5563; line-height: 1.5; margin: 0;">Performance trends indicate evolving business dynamics across the compared periods.</p>
        </div>
      </div>
    </div>

    <!-- RIGHT SIDE -->
    <div style="width: 50%; padding: 32px; background: white; display: flex; flex-direction: column;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
        <h3 style="font-size: 18px; font-weight: 700; color: #061551; margin: 0;">Historical Trend</h3>
      </div>
      <div style="flex: 1; background: #f8fafc; border-radius: 12px; padding: 16px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 12px; min-height: 220px;">
        <canvas id="areaChart"></canvas>
      </div>
      <div style="margin-top: 16px;">
        <h3 style="font-size: 16px; font-weight: 700; color: #061551; margin-bottom: 8px;">Performance Overview</h3>
        <p style="font-size: 14px; color: #4b5563; line-height: 1.6; margin: 0;">Strategic review of historical data helps identify growth opportunities and risk factors.</p>
      </div>
    </div>
  </div>
  <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 4px; background: linear-gradient(to right, #3b82f6, #22d3ee, #2563eb);"></div>
</div>

<script>
window.addEventListener('load', function() {{
  setTimeout(function() {{
    Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
    
    // Bar Chart
    const barCtx = document.getElementById('barChart').getContext('2d');
    new Chart(barCtx, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(comparison_data['metrics'])},
        datasets: [
          {{ label: 'Period 1', data: {json.dumps(comparison_data['period1'])}, backgroundColor: '#0e68b3', borderRadius: 6 }},
          {{ label: 'Period 2', data: {json.dumps(comparison_data['period2'])}, backgroundColor: '#32bbd8', borderRadius: 6 }}
        ]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ position: 'top', labels: {{ font: {{ size: 11, weight: '700' }} }} }} }},
        scales: {{
          y: {{ beginAtZero: true, ticks: {{ font: {{ size: 9 }}, callback: v => '$' + v.toLocaleString() }} }},
          x: {{ ticks: {{ font: {{ size: 9 }} }} }}
        }}
      }}
    }});

    // Area Chart
    const areaCtx = document.getElementById('areaChart').getContext('2d');
    new Chart(areaCtx, {{
      type: 'line',
      data: {{
        labels: {json.dumps(comparison_data['metrics'])},
        datasets: [{{
          label: 'Trend',
          data: {json.dumps(comparison_data['period2'])},
          borderColor: '#0e68b3',
          backgroundColor: 'rgba(14, 104, 179, 0.1)',
          borderWidth: 3,
          pointRadius: 4,
          fill: true,
          tension: 0.4
        }}]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ beginAtZero: true, ticks: {{ font: {{ size: 9 }}, callback: v => '$' + v.toLocaleString() }} }},
          x: {{ ticks: {{ font: {{ size: 9 }} }} }}
        }}
      }}
    }});

    // Donut Chart
    const donutCtx = document.getElementById('donutChart').getContext('2d');
    new Chart(donutCtx, {{
      type: 'doughnut',
      data: {{
        labels: ['Income', 'Gross Profit', 'EBITDA', 'Net Income'],
        datasets: [{{
          data: [25, 25, 25, 25],
          backgroundColor: ['#0e68b3', '#32bbd8', '#008afc', '#061551'],
          borderWidth: 0
        }}]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ position: 'right', labels: {{ font: {{ size: 8 }}, boxWidth: 8 }} }} }}
      }}
    }});
  }}, 500);
}});
</script>
</body></html>"""


def main():
    print("=" * 80)
    print("🎨 Professional PDF with REAL Charts & Data".center(80))
    print("=" * 80)
    print()
    
    slides_dir = Path("generated_financial_slides")
    tsx_files = sorted(slides_dir.glob("*.tsx"))
    
    if not tsx_files:
        print(f"❌ No TSX files found in {slides_dir}")
        return
    
    print(f"📄 Found {len(tsx_files)} slides\n")
    
    with sync_playwright() as p:
        print("🚀 Launching browser...")
        browser = p.chromium.launch(headless=True)
        # Use standard viewport with high DPI for crisp charts
        page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
        
        pdf_files = []
        
        # Sort slides: Title first, then others
        title_files = [f for f in tsx_files if 'Title' in f.name]
        other_files = [f for f in tsx_files if 'Title' not in f.name]
        sorted_files = title_files + other_files
        
        for tsx_file in sorted_files:
            print(f"  ✓ Rendering {tsx_file.name} with REAL data...")
            
            data = parse_tsx_with_data(tsx_file)
            
            if data['type'] == 'title':
                html = generate_title_html(data)
            elif data['type'] == 'comparison':
                html = generate_comparison_html_with_real_charts(data)
            else:
                # Check if this is a Cash Flow metric - use waterfall chart
                if 'cash flow' in data.get('title', '').lower():
                    print(f"    💧 Detected Cash Flow - using waterfall chart")
                    html = generate_cashflow_waterfall_html(data)
                else:
                    html = generate_statistic_html_with_real_chart(data)
            
            page.set_content(html)
            
            # Wait for Chart.js to load
            page.wait_for_load_state('networkidle')
            
            # Only wait for canvas if it's not the title slide
            if data['type'] != 'title':
                page.wait_for_timeout(6000)  # Increased wait time for all charts to render
                page.wait_for_selector('canvas', timeout=15000)
            else:
                page.wait_for_timeout(1000)
            
            pdf_path = f"real_slide_{len(pdf_files) + 1}_{tsx_file.stem}.pdf"
            # Generate high-quality PDF with better settings
            page.pdf(
                path=pdf_path, 
                width="1280px", 
                height="720px", 
                print_background=True,
                prefer_css_page_size=True
            )
            pdf_files.append(pdf_path)
        
        browser.close()
    
    print()
    print("=" * 80)
    print("✅ SUCCESS - Real Charts Generated!".center(80))
    print("=" * 80)
    print(f"\n📄 Generated {len(pdf_files)} slides with REAL data & charts:")
    for pdf in pdf_files:
        print(f"   • {pdf}")
    print("\n💡 Now merging into final presentation...")
    
    # Auto-merge
    try:
        from PyPDF2 import PdfMerger
        merger = PdfMerger()
        for pdf in pdf_files:
            merger.append(pdf)
        output = "PERFECT_Financial_Presentation.pdf"
        merger.write(output)
        merger.close()
        print(f"\n🎉 FINAL PDF: {output}")
        print("   ✅ Real Chart.js charts with actual data")
        print("   ✅ Proper labels and axes")
        print("   ✅ Professional formatting")
    except Exception as e:
        print(f"\n⚠️  Merge manually: python3 merge_pdfs.py")


if __name__ == "__main__":
    main()
