
"""
Generate PDF with REAL charts using actual financial data.
Uses Chart.js for proper data visualization.
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json
import re
import base64

def get_logo_base64():
    """Convert logo to base64 for embedding in HTML."""
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
    logo_src = get_logo_base64()
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Financial Report</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
body {{
  margin: 0;
  width: 1280px;
  height: 720px;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}
.gradient-bg {{
  background: linear-gradient(135deg, #061551 0%, #0a4d8f 50%, #0e68b3 100%);
}}
.accent-gradient {{
  background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
}}
.glass-effect {{
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}}
@keyframes float {{
  0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
  50% {{ transform: translateY(-20px) rotate(5deg); }}
}}
.float-animation {{
  animation: float 6s ease-in-out infinite;
}}
@keyframes pulse-glow {{
  0%, 100% {{ opacity: 0.15; }}
  50% {{ opacity: 0.25; }}
}}
.pulse-glow {{
  animation: pulse-glow 4s ease-in-out infinite;
}}
</style>
</head>
<body>
<div class="w-[1280px] h-[720px] gradient-bg relative overflow-hidden">
  
  <!-- Animated Background Elements -->
  <div class="absolute top-[-10%] right-[-5%] w-[500px] h-[500px] bg-blue-400 rounded-full opacity-15 blur-3xl pulse-glow"></div>
  <div class="absolute bottom-[-10%] left-[-5%] w-[450px] h-[450px] bg-cyan-400 rounded-full opacity-15 blur-3xl pulse-glow" style="animation-delay: 2s;"></div>
  <div class="absolute top-[30%] right-[10%] w-[300px] h-[300px] bg-blue-500 rounded-full opacity-10 blur-2xl float-animation"></div>
  
  <!-- Geometric Accents -->
  <div class="absolute top-[15%] right-[20%] w-16 h-16 border-2 border-blue-400 opacity-20 rotate-45"></div>
  <div class="absolute bottom-[25%] left-[15%] w-20 h-20 border-2 border-cyan-400 opacity-20 rotate-12"></div>
  
  <!-- Header Bar -->
  <div class="absolute top-0 left-0 right-0 px-16 py-8 flex justify-between items-center z-20">
    <div class="flex items-center space-x-4">
      <div class="w-14 h-14 bg-white rounded-2xl flex items-center justify-center shadow-2xl shadow-blue-500/30 p-2">
        <img src="{logo_src}" 
             alt="DashAnalytix Logo" 
             class="w-full h-full object-contain">
      </div>
      <div>
        <div class="text-2xl font-bold text-white tracking-tight">DashAnalytix</div>
        <div class="text-xs text-blue-300 font-medium tracking-wider">FINANCIAL INTELLIGENCE</div>
      </div>
    </div>
    <div class="glass-effect px-6 py-2 rounded-full">
      <span class="text-blue-200 font-semibold text-sm">CONFIDENTIAL</span>
    </div>
  </div>
  
  <!-- Main Content Area -->
  <div class="relative h-full flex flex-col justify-center px-16 z-10">
    <div class="max-w-5xl">
      
      <!-- Category Badge -->
      <div class="inline-flex items-center space-x-2 px-5 py-2 glass-effect rounded-full mb-8">
        <div class="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
        <span class="text-cyan-300 font-bold text-sm tracking-widest uppercase">Financial Report</span>
      </div>
      
      <!-- Main Title -->
      <h1 class="text-7xl font-black text-white leading-[1.1] mb-8 tracking-tight">
        {data['title']}
      </h1>
      
      <!-- Subtitle with Accent Line -->
      <div class="flex items-center space-x-5 mb-10">
        <div class="w-1.5 h-16 accent-gradient rounded-full shadow-lg shadow-blue-500/50"></div>
        <h2 class="text-3xl font-bold text-blue-100 leading-tight">
          {data['subtitle']}
        </h2>
      </div>
      
      <!-- Metadata Row -->
      <div class="flex items-center space-x-10 text-blue-200">
        <div class="flex items-center space-x-3 glass-effect px-5 py-3 rounded-xl">
          <svg class="w-6 h-6 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
          </svg>
          <div>
            <div class="text-xs text-blue-300 font-medium">Report Date</div>
            <div class="font-bold text-white">{data.get('date', 'October 2024')}</div>
          </div>
        </div>
        
        <div class="flex items-center space-x-3 glass-effect px-5 py-3 rounded-xl">
          <svg class="w-6 h-6 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <div>
            <div class="text-xs text-blue-300 font-medium">Document Type</div>
            <div class="font-bold text-white">{data.get('doc_type', 'Executive Summary')}</div>
          </div>
        </div>
        
        <div class="flex items-center space-x-3 glass-effect px-5 py-3 rounded-xl">
          <svg class="w-6 h-6 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/>
          </svg>
          <div>
            <div class="text-xs text-blue-300 font-medium">Prepared By</div>
            <div class="font-bold text-white">{data.get('prepared_by', 'Analytics Team')}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <!-- Footer Bar -->
  <div class="absolute bottom-0 left-0 right-0 px-16 py-6 bg-gradient-to-r from-black/40 via-black/30 to-black/40 backdrop-blur-md border-t border-white/10">
    <div class="flex justify-between items-center text-blue-100">
      <div class="flex items-center space-x-12 text-sm">
        <div class="flex items-center space-x-2">
          <svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
          <span class="font-semibold">{data.get('email', 'contact@dashanalytix.com')}</span>
        </div>
        <div class="flex items-center space-x-2">
          <svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
          </svg>
          <span class="font-semibold">{data.get('website', 'www.app.dashanalytix.com')}</span>
        </div>
      </div>
      <div class="flex items-center space-x-3">
        <div class="text-sm font-bold">{data.get('organization', 'Organization 1')}</div>
        <div class="w-2 h-2 bg-cyan-400 rounded-full"></div>
        <div class="text-sm opacity-70">Page 1</div>
      </div>
    </div>
  </div>
</div>
</body>
</html>"""


def generate_statistic_html_with_real_chart(data):
    """Generate premium statistic slide with enhanced visuals and REAL Chart.js chart."""
    # Generate bullet points with enhanced styling
    bullets_html = ''.join([
        f'''<div class="flex items-start bg-white rounded-lg p-3 shadow-sm hover:shadow-md transition-all duration-300 group">
                <div class="flex-shrink-0 w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center mr-3 group-hover:scale-110 transition-transform">
                    <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                    </svg>
                </div>
                <span class="text-xs font-semibold text-gray-700 pt-0.5">{bullet}</span>
            </div>'''
        for bullet in data['bullets'][:4]
    ])
    
    # Build KPI cards from parsed KPI fields - ONLY show ONE relevant comparison
    kpi_cards = []
    print(f"   🔍 KPI Data Check: prev='{data.get('kpi_prev_percent')}', yoy='{data.get('kpi_yoy_percent')}'")
    
    # Prioritize the main comparison (usually MoM/QoQ) over YoY - show only ONE card
    if data.get('kpi_prev_percent'):
        kpi_cards.append(f'''
                <div class="stat-card rounded-xl p-3">
                    <div class="text-2xl font-black text-white mb-1">{data['kpi_prev_percent']}</div>
                    <div class="text-xs font-semibold text-blue-200 uppercase tracking-wide">{data.get('kpi_prev_label', 'vs Previous')}</div>
                </div>''')
        print(f"   ✅ Added Primary KPI card: {data['kpi_prev_percent']} ({data.get('kpi_prev_label')})")
    elif data.get('kpi_yoy_percent'):
        # Only show YoY if no primary comparison exists
        kpi_cards.append(f'''
                <div class="stat-card rounded-xl p-3">
                    <div class="text-2xl font-black text-white mb-1">{data['kpi_yoy_percent']}</div>
                    <div class="text-xs font-semibold text-blue-200 uppercase tracking-wide">{data.get('kpi_yoy_label', 'YoY')}</div>
                </div>''')
        print(f"   ✅ Added YoY KPI card: {data['kpi_yoy_percent']} ({data.get('kpi_yoy_label')})")
    
    kpi_cards_html = ('\n'.join(kpi_cards)) if kpi_cards else ''
    
    if not kpi_cards_html:
        print(f"   ⚠️  NO KPI CARDS generated - no KPI data found")
    
    # Use ONLY actual data from TSX - NO FALLBACKS, NO HARDCODED DATA
    if data['chart_data'] and len(data['chart_data']) > 0:
        labels = [point.get('name', '') for point in data['chart_data']]
        values = [point.get('series1', 0) for point in data['chart_data']]
        chart_data_json = json.dumps({'labels': labels, 'values': values})
        print(f"   ✅ Using {len(labels)} real data points from TSX")
    else:
        # NO DATA - Show empty chart with message
        chart_data_json = json.dumps({
            'labels': ['No Data'],
            'values': [0]
        })
        print(f"   ⚠️  NO DATA FOUND - AI did not extract chart data for {data.get('title', 'this metric')}")
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
        * {{ font-family: 'Inter', sans-serif; }}
        body {{ margin:0; width:1280px; height:720px; overflow:hidden; background:#000 }}
        .gradient-left {{ 
            background:linear-gradient(135deg,#0a1628 0%,#1e3a8a 50%,#1e40af 100%);
            position:relative;
            overflow:hidden;
        }}
        .gradient-left::before {{
            content:'';
            position:absolute;
            top:-50%;
            right:-50%;
            width:100%;
            height:100%;
            background:radial-gradient(circle,rgba(96,165,250,0.15) 0%,transparent 70%);
            animation:float 8s ease-in-out infinite;
        }}
        .gradient-left::after {{
            content:'';
            position:absolute;
            bottom:-30%;
            left:-30%;
            width:80%;
            height:80%;
            background:radial-gradient(circle,rgba(147,197,253,0.1) 0%,transparent 60%);
            animation:float 6s ease-in-out infinite reverse;
        }}
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
        @keyframes shimmer {{
            0% {{ background-position: -1000px 0; }}
            100% {{ background-position: 1000px 0; }}
        }}
        .animate-slide-in {{ animation:slideIn 0.6s ease-out forwards; }}
        .delay-1 {{ animation-delay:0.1s; opacity:0; }}
        .delay-2 {{ animation-delay:0.2s; opacity:0; }}
        .delay-3 {{ animation-delay:0.3s; opacity:0; }}
        .delay-4 {{ animation-delay:0.4s; opacity:0; }}
        .glass-card {{
            background:rgba(255,255,255,0.95);
            backdrop-filter:blur(10px);
            border:1px solid rgba(255,255,255,0.3);
            box-shadow:0 8px 32px rgba(0,0,0,0.08);
        }}
        .stat-card {{
            background:linear-gradient(135deg,rgba(255,255,255,0.1) 0%,rgba(255,255,255,0.05) 100%);
            backdrop-filter:blur(10px);
            border:1px solid rgba(255,255,255,0.2);
            transition:all 0.3s ease;
        }}
        .stat-card:hover {{
            background:linear-gradient(135deg,rgba(255,255,255,0.15) 0%,rgba(255,255,255,0.08) 100%);
            transform:translateY(-2px);
            box-shadow:0 8px 24px rgba(0,0,0,0.2);
        }}
        canvas {{ image-rendering:-webkit-optimize-contrast; image-rendering:crisp-edges }}
        .metric-number {{
            background:linear-gradient(135deg,#60a5fa 0%,#3b82f6 50%,#2563eb 100%);
            -webkit-background-clip:text;
            -webkit-text-fill-color:transparent;
            background-clip:text;
            filter:drop-shadow(0 2px 4px rgba(59,130,246,0.3));
        }}
    </style>
</head>
<body>
    <div class="w-[1280px] h-[720px] bg-white flex relative">
        <!-- Left Panel -->
        <div class="w-1/2 gradient-left px-12 py-8 text-white relative z-10">
            <div class="inline-block px-4 py-1.5 bg-blue-400 bg-opacity-20 rounded-full mb-4 animate-slide-in border border-blue-300 border-opacity-30">
                <span class="text-blue-100 font-bold text-xs tracking-widest">METRIC ANALYSIS</span>
            </div>
            <h1 class="text-4xl font-black mb-3 animate-slide-in delay-1 leading-tight">{data['title']}</h1>
            <p class="text-sm font-medium mb-4 text-blue-100 animate-slide-in delay-2">{data['subtitle']}</p>
            <div class="w-24 h-1 bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-500 mb-6 rounded-full animate-slide-in delay-2"></div>
            
            <div class="animate-slide-in delay-3">
                <div class="text-7xl font-black metric-number mb-3">{data['value']}</div>
                <h2 class="text-xl font-bold mb-6 text-blue-50">{data['label']}</h2>
            </div>


            {f'<div class="mb-6 animate-slide-in delay-4">{kpi_cards_html}</div>' if kpi_cards_html else ''}
            
            <div class="animate-slide-in delay-4">
                <div class="w-full h-32 stat-card rounded-2xl p-3 shadow-2xl">
                    <canvas id="miniChart"></canvas>
                </div>
            </div>
            
            <div class="absolute top-8 right-8 w-4 h-4 bg-cyan-400 rounded-full" style="animation:pulse-glow 2s ease-in-out infinite"></div>
            <div class="absolute bottom-12 left-8 w-3 h-3 bg-blue-400 rounded-full opacity-60"></div>
            <div class="absolute top-1/3 right-16 w-2 h-2 bg-blue-300 rounded-full opacity-40"></div>
        </div>
        
        <!-- Right Panel -->
        <div class="w-1/2 bg-gradient-to-br from-gray-50 to-gray-100 px-10 py-8 relative">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-black text-gray-800">Performance Trend</h3>
                <div class="flex items-center space-x-2 bg-white px-3 py-1.5 rounded-full shadow-sm">
                    <div class="w-2.5 h-2.5 rounded-full bg-gradient-to-r from-blue-500 to-blue-600"></div>
                    <span class="text-xs font-bold text-gray-700">{data['title']}</span>
                </div>
            </div>
            <div class="h-52 glass-card rounded-2xl shadow-lg p-5 mb-4 animate-slide-in delay-2">
                <canvas id="myChart"></canvas>
            </div>
            <div class="h-28 glass-card rounded-2xl shadow-lg p-3 mb-4 animate-slide-in delay-3">
                <canvas id="areaChart"></canvas>
            </div>
            <div class="space-y-2 animate-slide-in delay-4">
                {bullets_html}
            </div>
        </div>
        <div class="absolute bottom-0 left-0 right-0 h-1.5 bg-gradient-to-r from-blue-600 via-cyan-400 to-blue-600"></div>
    </div>


    <script>
        // Wait for Chart.js to load
        window.addEventListener('load', function() {{
            setTimeout(function() {{
                // Register datalabels plugin
                Chart.register(ChartDataLabels);


                // Set Chart.js defaults for high quality
                Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
                Chart.defaults.plugins.legend.labels.usePointStyle = true;


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
                            pointRadius: 8,
                            pointBackgroundColor: '#2563eb',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 3,
                            pointHoverRadius: 10,
                            pointHoverBorderWidth: 4,
                            tension: 0.4,
                            fill: true
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        layout: {{
                            padding: {{
                                top: 45,
                                right: 20,
                                bottom: 15,
                                left: 10
                            }}
                        }},
                        plugins: {{
                            legend: {{
                                display: false
                            }},
                            datalabels: {{
                                display: true,
                                align: 'top',
                                anchor: 'end',
                                offset: 8,
                                color: '#1e40af',
                                backgroundColor: 'rgba(255, 255, 255, 0.98)',
                                borderRadius: 6,
                                borderWidth: 2,
                                borderColor: '#3b82f6',
                                padding: {{
                                    top: 6,
                                    bottom: 6,
                                    left: 10,
                                    right: 10
                                }},
                                font: {{
                                    size: 12,
                                    weight: '800',
                                    family: "'Inter', sans-serif"
                                }},
                                formatter: function(value) {{
                                    if (value >= 1000000) {{
                                        return '$' + (value / 1000000).toFixed(1) + 'M';
                                    }} else if (value >= 1000) {{
                                        return '$' + (value / 1000).toFixed(0) + 'K';
                                    }}
                                    return '$' + value.toLocaleString();
                                }},
                                clip: false
                            }},
                            tooltip: {{
                                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                                padding: 16,
                                titleFont: {{ size: 15, weight: 'bold' }},
                                bodyFont: {{ size: 14 }},
                                cornerRadius: 8,
                                displayColors: false,
                                callbacks: {{
                                    label: function(context) {{
                                        return '$' + context.parsed.y.toLocaleString();
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                grace: '15%',
                                ticks: {{
                                    callback: function(value) {{
                                        return '$' + (value/1000000).toFixed(1) + 'M';
                                    }},
                                    font: {{ size: 12, weight: '600' }},
                                    color: '#64748b'
                                }},
                                grid: {{
                                    color: 'rgba(0, 0, 0, 0.04)',
                                    lineWidth: 1
                                }},
                                border: {{ display: false }}
                            }},
                            x: {{
                                ticks: {{
                                    font: {{ size: 12, weight: '600' }},
                                    color: '#64748b'
                                }},
                                grid: {{
                                    display: false
                                }},
                                border: {{ display: false }}
                            }}
                        }},
                        interaction: {{
                            intersect: false,
                            mode: 'index'
                        }}
                    }}
                }});


                // Mini Area Chart on left side
                const miniCtx = document.getElementById('miniChart').getContext('2d');
                new Chart(miniCtx, {{
                    type: 'line',
                    data: {{
                        labels: chartData.labels,
                        datasets: [{{
                            data: chartData.values,
                            borderColor: '#60a5fa',
                            backgroundColor: function(context) {{
                                const ctx = context.chart.ctx;
                                const gradient = ctx.createLinearGradient(0, 0, 0, 160);
                                gradient.addColorStop(0, 'rgba(96, 165, 250, 0.5)');
                                gradient.addColorStop(1, 'rgba(96, 165, 250, 0.05)');
                                return gradient;
                            }},
                            borderWidth: 3,
                            pointRadius: 4,
                            pointBackgroundColor: '#60a5fa',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            tension: 0.4,
                            fill: true
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{ 
                            legend: {{ display: false }},
                            datalabels: {{ display: false }},
                            tooltip: {{
                                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                                padding: 12,
                                cornerRadius: 6,
                                callbacks: {{
                                    label: function(context) {{
                                        return '$' + (context.parsed.y/1000000).toFixed(1) + 'M';
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            y: {{ display: false, beginAtZero: true }},
                            x: {{ display: false }}
                        }}
                    }}
                }});


                // Bar Chart on right side bottom
                const areaCtx = document.getElementById('areaChart').getContext('2d');
                new Chart(areaCtx, {{
                    type: 'bar',
                    data: {{
                        labels: chartData.labels,
                        datasets: [{{
                            data: chartData.values,
                            backgroundColor: function(context) {{
                                const chart = context.chart;
                                const {{ctx, chartArea}} = chart;
                                if (!chartArea) return '#2563eb';
                                const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                                gradient.addColorStop(0, '#3b82f6');
                                gradient.addColorStop(1, '#2563eb');
                                return gradient;
                            }},
                            borderColor: '#1e40af',
                            borderWidth: 0,
                            borderRadius: 6,
                            hoverBackgroundColor: '#1e40af'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{ 
                            legend: {{ display: false }},
                            datalabels: {{ display: false }},
                            tooltip: {{
                                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                                padding: 14,
                                cornerRadius: 8,
                                callbacks: {{
                                    label: function(context) {{
                                        return '$' + (context.parsed.y/1000000).toFixed(1) + 'M';
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            y: {{ 
                                display: true,
                                beginAtZero: true,
                                ticks: {{ 
                                    font: {{ size: 10, weight: '600' }},
                                    color: '#64748b',
                                    callback: function(value) {{ return '$' + (value/1000000).toFixed(1) + 'M'; }}
                                }},
                                grid: {{ 
                                    color: 'rgba(0, 0, 0, 0.04)',
                                    lineWidth: 1
                                }},
                                border: {{ display: false }}
                            }},
                            x: {{ 
                                ticks: {{ 
                                    font: {{ size: 11, weight: '600' }},
                                    color: '#64748b'
                                }},
                                grid: {{ display: false }},
                                border: {{ display: false }}
                            }}
                        }}
                    }}
                }});
            }}, 500);
        }});
    </script>
</body></html>"""


def generate_comparison_html_with_real_charts(data):
    """Generate premium comparison dashboard slide with comprehensive financial overview."""
    # Extract comparison data from TSX chart_data for all metrics
    financial_metrics = []
    operational_metrics = []
    period1_values = []
    period2_values = []
    period1_label = "Previous Period"
    period2_label = "Current Period"
    
    if data.get('chart_data') and len(data['chart_data']) > 0:
        for point in data['chart_data']:
            metric_name = point.get('name', 'Metric')
            series1 = point.get('series1', 0)
            series2 = point.get('series2', 0)
            
            # Categorize metrics for different sections
            if any(keyword in metric_name.lower() for keyword in ['income', 'revenue', 'profit', 'ebitda', 'expense', 'cost']):
                financial_metrics.append(metric_name)
                period1_values.append(series1)
                period2_values.append(series2)
            elif any(keyword in metric_name.lower() for keyword in ['collection', 'payment', 'inventory', 'days']):
                operational_metrics.append({
                    'name': metric_name,
                    'period1': series1,
                    'period2': series2,
                    'change': series2 - series1,
                    'change_pct': ((series2 - series1) / series1 * 100) if series1 != 0 else 0
                })
        
        # Extract period labels from first data point if available
        if len(data['chart_data']) > 0:
            first_point = data['chart_data'][0]
            period1_label = first_point.get('period1_label', period1_label)
            period2_label = first_point.get('period2_label', period2_label)
        
        print(f"   ✅ Dashboard: {len(financial_metrics)} financial + {len(operational_metrics)} operational metrics")
    else:
        # No data - show message
        comparison_data = {
            'metrics': ['No Data'],
            'period1': [0],
            'period2': [0]
        }
        print(f"   ⚠️  NO COMPARISON DATA FOUND")
    
    # Generate financial metric cards with percentage changes
    financial_cards_html = ""
    if len(financial_metrics) >= 1:  # Generate cards if we have any financial metrics
        cards_to_show = min(5, len(financial_metrics))  # Show up to 5 cards
        for i in range(cards_to_show):
            metric = financial_metrics[i]
            p1_val = period1_values[i]
            p2_val = period2_values[i]
            change_pct = ((p2_val - p1_val) / p1_val * 100) if p1_val != 0 else 0
            sign = "+" if change_pct >= 0 else ""
            color = "blue" if "income" in metric.lower() or "revenue" in metric.lower() else "cyan" if "profit" in metric.lower() else "indigo" if "ebitda" in metric.lower() else "orange" if "expense" in metric.lower() else "blue"
            
            financial_cards_html += f'''
        <div class="metric-card glass-card rounded-xl p-3 shadow-md text-center border-l-4 border-{color}-600">
          <div class="text-2xl font-black text-{color}-600">{sign}{change_pct:.1f}%</div>
          <div class="text-xs font-semibold text-gray-600 mt-1">{metric[:8]}</div>
        </div>'''
        
        # Fill remaining slots with placeholder cards if we have fewer than 5
        while len(financial_cards_html.split('<div class="metric-card')) - 1 < 5:
            financial_cards_html += '''
        <div class="metric-card glass-card rounded-xl p-3 shadow-md text-center border-l-4 border-gray-300">
          <div class="text-2xl font-black text-gray-400">--</div>
          <div class="text-xs font-semibold text-gray-400 mt-1">N/A</div>
        </div>'''
    
    # Generate operational metric cards
    operational_cards_html = ""
    if operational_metrics:
        for i, metric in enumerate(operational_metrics[:3]):
            change = metric['change']
            change_pct = metric['change_pct']
            sign = "+" if change >= 0 else ""
            bg_color = "red" if change > 0 else "green"
            arrow_direction = "up" if change > 0 else "down"
            
            operational_cards_html += f'''
        <div class="glass-card rounded-xl p-3 shadow-md border-l-4 border-blue-600 hover:shadow-lg transition-all duration-300">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-xs font-semibold text-gray-500 mb-0.5">{metric['name']}</div>
              <div class="flex items-baseline space-x-2">
                <span class="text-2xl font-black text-blue-600">{metric['period1']:.0f}</span>
                <span class="text-sm font-bold text-gray-400">→ {metric['period2']:.0f}</span>
                <span class="text-xs px-2 py-0.5 bg-{bg_color}-100 text-{bg_color}-700 rounded-full font-bold">{sign}{change:.0f}</span>
              </div>
            </div>
            <svg class="w-8 h-8 text-{"green" if change < 0 else "red"}-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M13 {"7h8m0 0v8m0-8l-8 8-4-4-6 6" if change < 0 else "17h8m0 0V9m0 8l-8-8-4 4-6-6"}"/>
            </svg>
          </div>
        </div>'''
    else:
        # Add placeholder operational cards if no operational data
        for i in range(3):
            operational_cards_html += '''
        <div class="glass-card rounded-xl p-3 shadow-md border-l-4 border-gray-300 hover:shadow-lg transition-all duration-300">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-xs font-semibold text-gray-400 mb-0.5">No Data</div>
              <div class="flex items-baseline space-x-2">
                <span class="text-2xl font-black text-gray-400">--</span>
                <span class="text-sm font-bold text-gray-400">→ --</span>
                <span class="text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full font-bold">N/A</span>
              </div>
            </div>
            <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"/>
            </svg>
          </div>
        </div>'''
    
    # Prepare chart data as JSON
    financial_data_json = {
        'metrics': financial_metrics[:5],
        'period1': period1_values[:5],
        'period2': period2_values[:5]
    }
    
    # Prepare operational line chart data
    operational_line_data = []
    for metric in operational_metrics[:3]:
        operational_line_data.append({
            'label': metric['name'],
            'data': [metric['period1'], metric['period2']]
        })
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
        * {{ font-family: 'Inter', sans-serif; }}
        body {{ margin:0; width:1280px; height:720px; overflow:hidden; background:#000 }}
        .gradient-header {{ 
            background:linear-gradient(135deg,#0a1628 0%,#1e3a8a 50%,#1e40af 100%);
            position:relative;
            overflow:hidden;
        }}
        .gradient-header::before {{
            content:'';
            position:absolute;
            top:-50%;
            right:-50%;
            width:100%;
            height:100%;
            background:radial-gradient(circle,rgba(96,165,250,0.15) 0%,transparent 70%);
            animation:float 8s ease-in-out infinite;
        }}
        .gradient-header::after {{
            content:'';
            position:absolute;
            bottom:-30%;
            left:-30%;
            width:80%;
            height:80%;
            background:radial-gradient(circle,rgba(147,197,253,0.1) 0%,transparent 60%);
            animation:float 6s ease-in-out infinite reverse;
        }}
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
        .animate-slide-in {{ animation:slideIn 0.6s ease-out forwards; }}
        .delay-1 {{ animation-delay:0.1s; opacity:0; }}
        .delay-2 {{ animation-delay:0.2s; opacity:0; }}
        .delay-3 {{ animation-delay:0.3s; opacity:0; }}
        .delay-4 {{ animation-delay:0.4s; opacity:0; }}
        .glass-card {{
            background:rgba(255,255,255,0.95);
            backdrop-filter:blur(10px);
            border:1px solid rgba(255,255,255,0.3);
            box-shadow:0 8px 32px rgba(0,0,0,0.08);
        }}
        .stat-card {{
            background:linear-gradient(135deg,rgba(255,255,255,0.1) 0%,rgba(255,255,255,0.05) 100%);
            backdrop-filter:blur(10px);
            border:1px solid rgba(255,255,255,0.2);
            transition:all 0.3s ease;
        }}
        .stat-card:hover {{
            background:linear-gradient(135deg,rgba(255,255,255,0.15) 0%,rgba(255,255,255,0.08) 100%);
            transform:translateY(-2px);
            box-shadow:0 8px 24px rgba(0,0,0,0.2);
        }}
        canvas {{ image-rendering:-webkit-optimize-contrast; image-rendering:crisp-edges }}
        .metric-card {{
            transition:all 0.3s ease;
        }}
        .metric-card:hover {{
            transform:translateY(-2px);
            box-shadow:0 8px 24px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
<div class="w-[1280px] h-[720px] bg-white relative">
  <div class="h-24 gradient-header px-12 py-6 flex justify-between items-center shadow-2xl relative z-10">
    <div>
      <div class="inline-block px-4 py-1.5 bg-blue-400 bg-opacity-20 rounded-full mb-2 border border-blue-300 border-opacity-30">
        <span class="text-blue-100 font-bold text-xs tracking-widest">COMPARATIVE ANALYSIS</span>
      </div>
      <h1 class="text-3xl font-black text-white">Business Health Dashboard</h1>
    </div>
    <div class="flex items-center space-x-3">
      <div class="w-11 h-11 bg-white bg-opacity-20 backdrop-blur-sm rounded-xl flex items-center justify-center">
        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
      </div>
      <span class="text-lg font-bold text-white">Financial Analysis</span>
    </div>
    <div class="absolute top-6 right-20 w-4 h-4 bg-cyan-400 rounded-full" style="animation:pulse-glow 2s ease-in-out infinite"></div>
    <div class="absolute bottom-6 left-32 w-3 h-3 bg-blue-400 rounded-full opacity-60"></div>
  </div>

  <div class="flex h-[calc(100%-96px)]">
    <!-- LEFT SIDE: FINANCIAL PERFORMANCE -->
    <div class="w-[55%] p-8 bg-gradient-to-br from-gray-50 to-blue-50 animate-slide-in">
      <div class="flex items-center justify-between mb-5">
        <div>
          <div class="inline-block px-3 py-1.5 glass-card rounded-lg mb-2 shadow-md">
            <span class="text-xs font-bold tracking-wide text-blue-600">FINANCIAL METRICS</span>
          </div>
          <h3 class="text-xl font-black text-gray-800">Performance Summary</h3>
        </div>
        <div class="flex space-x-2">
          <div class="flex items-center space-x-2 px-4 py-2 glass-card rounded-xl shadow-md">
            <div class="w-3 h-3 rounded-full bg-gradient-to-r from-blue-500 to-blue-600"></div>
            <span class="text-xs font-bold text-gray-700">{period1_label}</span>
          </div>
          <div class="flex items-center space-x-2 px-4 py-2 glass-card rounded-xl shadow-md">
            <div class="w-3 h-3 rounded-full bg-gradient-to-r from-cyan-400 to-cyan-500"></div>
            <span class="text-xs font-bold text-gray-700">{period2_label}</span>
          </div>
        </div>
      </div>
      <div class="h-[340px] glass-card rounded-2xl shadow-lg p-5 mb-4 animate-slide-in delay-1">
        <canvas id="barChart"></canvas>
      </div>
      <div class="grid grid-cols-5 gap-2 animate-slide-in delay-2">
        {financial_cards_html}
      </div>
    </div>

    <!-- RIGHT SIDE: OPERATIONAL EFFICIENCY -->
    <div class="w-[45%] p-6 bg-white animate-slide-in delay-1">
      <div class="mb-4">
        <div class="inline-block px-3 py-1.5 rounded-lg mb-2 shadow-md bg-gradient-to-r from-cyan-500 to-blue-600">
          <span class="text-xs font-bold tracking-wide text-white">OPERATIONAL EFFICIENCY</span>
        </div>
        <h3 class="text-xl font-black text-gray-800">Working Capital</h3>
      </div>

      <div class="h-[170px] glass-card rounded-2xl shadow-lg p-4 mb-3 animate-slide-in delay-2">
        <canvas id="lineChart"></canvas>
      </div>

      <div class="space-y-2.5 animate-slide-in delay-3">
        {operational_cards_html}
      </div>
    </div>
  </div>
  <div class="absolute bottom-0 left-0 right-0 h-1.5 bg-gradient-to-r from-blue-600 via-cyan-400 to-blue-600"></div>
</div>

<script>
// Wait for Chart.js to load
window.addEventListener('load', function() {{
  setTimeout(function() {{
// Set Chart.js defaults for high quality
Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
Chart.defaults.plugins.legend.labels.usePointStyle = true;

// Financial metrics data from extracted TSX
const financial_data = {json.dumps(financial_data_json)};

// Bar Chart - Financial Performance
const barCtx = document.getElementById('barChart').getContext('2d');
new Chart(barCtx, {{
  type: 'bar',
  data: {{
    labels: financial_data['metrics'],
    datasets: [
      {{
        label: '{period1_label}',
        data: financial_data['period1'],
        backgroundColor: function(context) {{
          const chart = context.chart;
          const {{ctx, chartArea}} = chart;
          if (!chartArea) return '#2563eb';
          const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
          gradient.addColorStop(0, '#3b82f6');
          gradient.addColorStop(1, '#2563eb');
          return gradient;
        }},
        borderColor: '#1e40af',
        borderWidth: 0,
        borderRadius: 8,
        barThickness: 32
      }},
      {{
        label: '{period2_label}',
        data: financial_data['period2'],
        backgroundColor: function(context) {{
          const chart = context.chart;
          const {{ctx, chartArea}} = chart;
          if (!chartArea) return '#06b6d4';
          const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
          gradient.addColorStop(0, '#22d3ee');
          gradient.addColorStop(1, '#06b6d4');
          return gradient;
        }},
        borderColor: '#0891b2',
        borderWidth: 0,
        borderRadius: 8,
        barThickness: 32
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{
        display: false
      }},
      tooltip: {{
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        padding: 14,
        titleFont: {{ size: 14, weight: 'bold' }},
        bodyFont: {{ size: 13 }},
        cornerRadius: 8,
        displayColors: true,
        usePointStyle: true,
        callbacks: {{
          label: function(context) {{
            return context.dataset.label + ': $' + context.parsed.y.toLocaleString();
          }}
        }}
      }}
    }},
    scales: {{
      y: {{
        beginAtZero: true,
        grid: {{
          color: 'rgba(0, 0, 0, 0.04)',
          lineWidth: 1
        }},
        ticks: {{
          callback: function(value) {{ return '$' + (value/1000) + 'K'; }},
          font: {{ size: 12, weight: '600' }},
          color: '#64748b'
        }},
        border: {{ display: false }}
      }},
      x: {{
        grid: {{ display: false }},
        ticks: {{ 
          font: {{ size: 12, weight: '600' }},
          color: '#64748b'
        }},
        border: {{ display: false }}
      }}
    }}
  }}
}});

// Line Chart - Operational Efficiency Trends
const lineCtx = document.getElementById('lineChart').getContext('2d');
const operationalData = {json.dumps([{{
    'labels': [period1_label, period2_label],
    'datasets': [{{
        'label': metric['name'],
        'data': [metric['period1'], metric['period2']],
        'borderColor': ['#2563eb', '#06b6d4', '#8b5cf6'][i % 3],
        'backgroundColor': f"rgba({{'37, 99, 235' if i == 0 else '6, 182, 212' if i == 1 else '139, 92, 246'}}, 0.1)"
    }} for i, metric in enumerate(operational_metrics[:3])]
}} if operational_metrics else {{'labels': [], 'datasets': []}})};

new Chart(lineCtx, {{
  type: 'line',
  data: operationalData,
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{
        display: true,
        position: 'bottom',
        labels: {{ 
          font: {{ size: 11, weight: 'bold' }},
          padding: 12,
          usePointStyle: true,
          pointStyle: 'circle'
        }}
      }},
      tooltip: {{
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        padding: 14,
        titleFont: {{ size: 13, weight: 'bold' }},
        bodyFont: {{ size: 12 }},
        cornerRadius: 8,
        displayColors: true,
        usePointStyle: true,
        callbacks: {{
          label: function(context) {{
            return context.dataset.label + ': ' + context.parsed.y + ' days';
          }}
        }}
      }}
    }},
    scales: {{
      y: {{
        beginAtZero: true,
        grid: {{
          color: 'rgba(0, 0, 0, 0.04)',
          lineWidth: 1
        }},
        ticks: {{
          callback: function(value) {{ return value + ' days'; }},
          font: {{ size: 11, weight: '600' }},
          color: '#64748b'
        }},
        border: {{ display: false }}
      }},
      x: {{
        grid: {{ display: false }},
        ticks: {{ 
          font: {{ size: 11, weight: '600' }},
          color: '#64748b'
        }},
        border: {{ display: false }}
      }}
    }}
  }}
}});

  }}, 500);
}});
</script>
</body></html>"""
  type: 'bar',
  data: {{
    labels: {json.dumps(comparison_data['metrics'])},
    datasets: [
      {{
        label: 'Period 1',
        data: {json.dumps(comparison_data['period1'])},
        backgroundColor: 'rgba(14, 104, 179, 0.85)',
        borderColor: '#0e68b3',
        borderWidth: 0,
        borderRadius: 6
      }},
      {{
        label: 'Period 2',
        data: {json.dumps(comparison_data['period2'])},
        backgroundColor: 'rgba(50, 187, 216, 0.85)',
        borderColor: '#32bbd8',
        borderWidth: 0,
        borderRadius: 6
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{
        display: true,
        position: 'top',
        labels: {{ font: {{ size: 12, weight: 'bold' }} }}
      }},
      tooltip: {{
        callbacks: {{
          label: function(context) {{
            return context.dataset.label + ': $' + context.parsed.y.toLocaleString();
          }}
        }}
      }}
    }},
    scales: {{
      y: {{
        beginAtZero: true,
        ticks: {{
          callback: function(value) {{ return '$' + value.toLocaleString(); }},
          font: {{ size: 10 }}
        }}
      }},
      x: {{
        ticks: {{ font: {{ size: 10 }} }}
      }}
    }}
  }}
}});

// Area Chart - use same data as bar chart but show trend
const areaCtx = document.getElementById('areaChart').getContext('2d');
new Chart(areaCtx, {{
  type: 'line',
  data: {{
    labels: {json.dumps(comparison_data['metrics'])},
    datasets: [{{
      label: 'Trend',
      data: {json.dumps(comparison_data['period2'])},
      borderColor: '#0e68b3',
      backgroundColor: 'rgba(14, 104, 179, 0.15)',
      borderWidth: 3,
      pointRadius: 5,
      pointBackgroundColor: '#0e68b3',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      fill: true,
      tension: 0.4
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          label: function(context) {{
            return '$' + context.parsed.y.toLocaleString();
          }}
        }}
      }}
    }},
    scales: {{
      y: {{
        beginAtZero: true,
        ticks: {{
          callback: function(value) {{ return '$' + value.toLocaleString(); }},
          font: {{ size: 10 }}
        }}
      }},
      x: {{
        ticks: {{ font: {{ size: 9 }} }}
      }}
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
      data: [5200, 5097, 5097, 5097],
      backgroundColor: ['#0e68b3', '#32bbd8', '#008afc', '#061551'],
      borderWidth: 0
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{
        display: true,
        position: 'right',
        labels: {{ font: {{ size: 8 }}, padding: 8 }}
      }}
    }}
  }}
}});

  }}, 1000);
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
