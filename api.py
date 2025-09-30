"""
Generate professional TSX slide components for financial reports.
Uses the professional slide template format.
"""
import json
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime

from openai_service import OpenAIService
from financial_models import FinancialReportData, TrendAnalysis, PeriodComparison


class FinancialTSXGenerator:
    """Generates TSX slide components for financial data."""
    
    def __init__(self):
        """Initialize the TSX generator."""
        self.openai_service = OpenAIService()
    
    def generate_financial_slides(
        self,
        financial_text: str,
        output_dir: str = "generated_slides"
    ) -> List[str]:
        """
        Generate TSX slide components from financial text.
        
        Args:
            financial_text: Raw financial analysis text
            output_dir: Directory to save generated slides
        Returns:
            Parsed financial data in JSON format
        """
        system_prompt = """You are a financial data analyst. Parse the financial text and extract structured data for TSX slide generation.

Return ONLY valid JSON with this structure:
{
    "title": "Financial Analysis Report",
    "subtitle": "May 2019 to Sep 2024",
    "date": "September 2024",
    "metrics": [
        {
            "name": "Income",
            "value": "$155,815",
            "label": "Peak Revenue (Dec 2020)",
            "description": "Income shows significant volatility...",
            "bullet_points": [
                "Peaked in December 2020 at $155,815",
                "Average income approximately $15,000",
                "Recent decline from $9,384 to $5,200"
            ],
            "chart_data": [
                {"name": "May 2019", "series1": 8321, "series2": 0, "series3": 0},
                {"name": "Dec 2020", "series1": 155815, "series2": 0, "series3": 0}
            ]
        }
    ],
    "comparisons": {
        "period1": "Aug 2024",
        "period2": "Sep 2024",
        "bar_chart_data": [
            {"name": "Income", "series1": 9384, "series2": 5200, "series3": 0},
            {"name": "Gross Profit", "series1": 9374, "series2": 5097, "series3": 0}
        ],
        "area_chart_data": [
            {"name": "Q1", "series1": 20, "series2": 30, "series3": 15}
        ]
    }
}"""

        user_prompt = f"""Parse this financial text and extract EVERY SINGLE number with its date/period:

{financial_text}

CRITICAL INSTRUCTIONS:
1. Find EVERY metric mentioned (Income, Gross Profit, EBITDA, Cost of Sales, Customer Collection Days, etc.)
2. For EACH metric, extract ALL values with their time periods
3. Create separate chart_data arrays for each metric with ALL data points

EXAMPLE from text "Income $88,912 in Feb 2021 vs $84,629 in Jan 2021":
- Income metric chart_data: [
    {{"name": "Jan 2021", "series1": 84629, "series2": 0, "series3": 0}},
    {{"name": "Feb 2021", "series1": 88912, "series2": 0, "series3": 0}}
  ]

EXAMPLE from text "Gross Profit $36,251 vs $40,371":
- Gross Profit metric chart_data: [
    {{"name": "Period 1", "series1": 40371, "series2": 0, "series3": 0}},
    {{"name": "Period 2", "series1": 36251, "series2": 0, "series3": 0}}
  ]

RULES:
- Extract EVERY number mentioned for each metric
- If dates are given (Jan 2021, Feb 2021), use them as "name"
- If no dates, use "Period 1", "Period 2", etc.
- Remove $ and commas from numbers (convert to integers)
- Create a separate metric entry for EACH different metric mentioned
- chart_data arrays must NEVER be empty if numbers exist in text

CRITICAL - Each metric MUST have:
1. "name": The metric name (e.g., "Income", "Gross Profit")
2. "value": The LATEST or MOST SIGNIFICANT value with $ (e.g., "$88,912" or "$10.9 days")
3. "label": A descriptive label (e.g., "Latest Period (Feb 2021)" or "Current Value")
4. "chart_data": Array of ALL data points found
5. "bullet_points": 3-5 key insights

Return complete JSON with ALL metrics and ALL their data points."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.openai_service.generate_completion(messages)
            parsed_data = json.loads(response)
            
            # Debug: Print what AI extracted
            print(f"\n🤖 AI Extracted Data:")
            print(f"   Metrics count: {len(parsed_data.get('metrics', []))}")
            for metric in parsed_data.get('metrics', []):  # Show ALL metrics
                chart_data = metric.get('chart_data', [])
                print(f"   - {metric.get('name')}: {len(chart_data)} data points")
                if chart_data:
                    for i, point in enumerate(chart_data[:3]):  # Show first 3 points
                        print(f"     [{i+1}] {point.get('name')}: ${point.get('series1', 0):,}")
                else:
                    print(f"     ⚠️  NO CHART DATA EXTRACTED!")
            
            return parsed_data
        except Exception as e:
            print(f"⚠️  Error parsing data: {e}")
            return self._create_default_structure(financial_text)
    
    def _create_default_structure(self, financial_text: str) -> Dict[str, Any]:
        """Create default structure if AI parsing fails."""
        return {
            "title": "Financial Analysis Report",
            "subtitle": "Comprehensive Financial Overview",
            "date": datetime.now().strftime("%B %Y"),
            "metrics": [],
            "comparisons": None
        }
    
    def _generate_title_slide(self, data: Dict[str, Any], output_path: Path) -> str:
        """Generate TitleSlide.tsx component."""
        tsx_content = f'''import * as z from "zod";
import {{ ImageSchema }} from "../defaultSchemes";

export const layoutName = "Financial Report Title";
export const layoutId = "financial-title-slide";
export const layoutDescription = "Title slide for financial analysis report";

export const Schema = z.object({{
  organizationName: z.string().default("Financial Analysis"),
  primaryTitle: z.string().default("{data.get('title', 'FINANCIAL REPORT')}"),
  secondaryTitle: z.string().default("{data.get('subtitle', 'COMPREHENSIVE ANALYSIS')}"),
  brandLogo: ImageSchema.default({{
    __image_url__: "https://via.placeholder.com/40x40/14B8A6/FFFFFF?text=FA",
    __image_prompt__: "Financial analytics logo with chart symbol"
  }}),
  contactDetails: z.object({{
    phoneNumber: z.string().default("+1-234-567-8900"),
    physicalAddress: z.string().default("123 Finance St, Business City, ST 12345"),
    websiteUrl: z.string().default("www.financial-analysis.com")
  }}).default({{
    phoneNumber: "+1-234-567-8900",
    physicalAddress: "123 Finance St, Business City, ST 12345",
    websiteUrl: "www.financial-analysis.com"
  }}),
  presentationDate: z.string().default("{data.get('date', datetime.now().strftime('%B %Y'))}"),
  showDecorations: z.boolean().default(true),
  showNavigationArrow: z.boolean().default(true),
}});

type SchemaType = z.infer<typeof Schema>;

const FinancialTitleSlide = ({{ data }}: {{ data: Partial<SchemaType> }}) => {{
  const {{
    organizationName,
    primaryTitle,
    secondaryTitle,
    brandLogo,
    contactDetails,
    presentationDate,
    showDecorations,
    showNavigationArrow,
  }} = data;

  return (
    <div className="aspect-video max-w-[1280px] w-full bg-white relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 px-16 py-8 flex justify-between items-center z-20">
        <div className="flex items-center space-x-3">
          {{brandLogo?.__image_url__ && (
            <div className="w-10 h-10">
              <img src={{brandLogo.__image_url__}} alt={{brandLogo.__image_prompt__}} className="w-full h-full object-contain" />
            </div>
          )}}
          {{organizationName && <span className="text-2xl font-bold text-gray-900">{{organizationName}}</span>}}
        </div>
        {{showNavigationArrow && (
          <div className="w-12 h-12 bg-teal-600 rounded-full flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={{2}} d="M9 5l7 7-7 7" />
            </svg>
          </div>
        )}}
      </div>

      {{showDecorations && <div className="absolute top-20 right-16 w-96 h-96 bg-yellow-100 rounded-full opacity-60 z-10"></div>}}

      <div className="relative h-full flex flex-col justify-center px-16">
        <div>
          {{primaryTitle && <h1 className="text-4xl lg:text-5xl font-black text-teal-700 leading-none tracking-tight mb-4">{{primaryTitle}}</h1>}}
          {{secondaryTitle && (
            <div className="flex items-center space-x-4 mb-12">
              <div className="w-4 h-4 bg-teal-600 rounded-full"></div>
              <h2 className="text-xl font-bold text-gray-800 tracking-wide">{{secondaryTitle}}</h2>
            </div>
          )}}
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 px-16 py-8 border-t-2 border-gray-300">
        <div className="flex justify-between items-center text-gray-700">
          <div className="flex space-x-16 text-sm">
            {{contactDetails?.phoneNumber && (
              <div><div className="font-semibold text-gray-900 mb-1">Telephone</div><div>{{contactDetails.phoneNumber}}</div></div>
            )}}
            {{contactDetails?.physicalAddress && (
              <div><div className="font-semibold text-gray-900 mb-1">Address</div><div>{{contactDetails.physicalAddress}}</div></div>
            )}}
            {{contactDetails?.websiteUrl && (
              <div><div className="font-semibold text-gray-900 mb-1">Website</div><div>{{contactDetails.websiteUrl}}</div></div>
            )}}
          </div>
          {{presentationDate && <div className="text-right"><div className="text-lg font-bold text-gray-900">{{presentationDate}}</div></div>}}
        </div>
      </div>
    </div>
  );
}};

export default FinancialTitleSlide;
'''
        
        file_path = output_path / "FinancialTitleSlide.tsx"
        file_path.write_text(tsx_content)
        print(f"  ✓ Created: {file_path}")
        return str(file_path)
    
    def _generate_statistic_slide(self, metric: Dict[str, Any], output_path: Path) -> str:
        """Generate StatisticSlide.tsx for a metric."""
        metric_name = metric.get("name", "Metric")
        safe_name = metric_name.replace(" ", "")
        
        # Format chart data
        chart_data_str = json.dumps(metric.get("chart_data", []), indent=6)
        bullet_points_str = json.dumps(metric.get("bullet_points", []), indent=6)
        
        tsx_content = f'''import React from "react";
import * as z from "zod";
import {{ ImageSchema }} from "../defaultSchemes";
import {{ ChartContainer, ChartTooltip, ChartTooltipContent }} from "@/components/ui/chart";
import {{ LineChart, Line, XAxis, YAxis, CartesianGrid }} from "recharts";

export const layoutName = "{metric_name} Statistics";
export const layoutId = "{safe_name.lower()}-statistic-slide";
export const layoutDescription = "Financial statistics for {metric_name}";

export const Schema = z.object({{
  sectionTitle: z.string().default("{metric_name.upper()}"),
  sectionSubtitle: z.string().default("FINANCIAL PERFORMANCE ANALYSIS"),
  statisticValue: z.string().default("{metric.get('value', 'N/A')}"),
  statisticLabel: z.string().default("{metric.get('label', metric_name)}"),
  supportingVisual: ImageSchema.default({{
    __image_url__: "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80",
    __image_prompt__: "Financial analytics dashboard with charts and data"
  }}),
  bulletPoints: z.array(z.string()).default({bullet_points_str}),
  chartData: z.array(z.object({{
    name: z.string(),
    series1: z.number(),
    series2: z.number(),
    series3: z.number(),
  }})).default({chart_data_str}),
  showYellowUnderline: z.boolean().default(true),
  showVisualAccents: z.boolean().default(true),
}});

const chartConfig = {{
  series1: {{ label: "Value", color: "#061551" }},
  series2: {{ label: "Trend", color: "#0e68b3" }},
  series3: {{ label: "Target", color: "#32bbd8" }},
}};

type SchemaType = z.infer<typeof Schema>;

const {safe_name}StatisticSlide = ({{ data }}: {{ data: Partial<SchemaType> }}) => {{
  const {{ sectionTitle, sectionSubtitle, statisticValue, statisticLabel, supportingVisual, bulletPoints, chartData, showYellowUnderline, showVisualAccents }} = data;

  return (
    <div className="aspect-video max-w-[1280px] w-full bg-white relative overflow-hidden">
      <div className="h-full flex">
        <div className="w-1/2 relative bg-teal-600 px-16 py-12 flex flex-col text-white">
          <div className="mb-8">
            {{sectionTitle && <h1 className="text-3xl lg:text-4xl font-black leading-tight mb-4">{{sectionTitle}}</h1>}}
            {{sectionSubtitle && <p className="text-base font-semibold tracking-wide mb-4">{{sectionSubtitle}}</p>}}
            {{showYellowUnderline && <div className="w-24 h-1 bg-yellow-300 mb-8"></div>}}
          </div>
          
          <div className="mb-8">
            {{statisticValue && <div className="text-8xl font-black text-yellow-300 mb-4">{{statisticValue}}</div>}}
            {{statisticLabel && <h2 className="text-2xl font-bold">{{statisticLabel}}</h2>}}
          </div>
          
          {{supportingVisual?.__image_url__ && (
            <div className="flex-1 flex items-end">
              <div className="w-full h-48">
                <img src={{supportingVisual.__image_url__}} alt={{supportingVisual.__image_prompt__}} className="w-full h-full object-cover rounded-lg" />
              </div>
            </div>
          )}}
          
          {{showVisualAccents && (
            <>
              <div className="absolute top-8 right-8 w-6 h-6 bg-yellow-300 rounded-full"></div>
              <div className="absolute bottom-12 left-8 w-4 h-4 bg-yellow-200 rounded-full"></div>
            </>
          )}}
        </div>

        <div className="w-1/2 relative bg-white px-16 py-12">
          <div className="flex-1 px-8 pt-8">
            <div className="flex items-center justify-end mb-4 space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-yellow-300 rounded-full"></div>
                <span className="text-sm text-gray-600">{{chartConfig.series1.label}}</span>
              </div>
            </div>
            
            {{chartData && chartData.length > 0 && (
              <div className="h-64">
                <ChartContainer config={{chartConfig}} className="h-full w-full">
                  <LineChart data={{chartData}} margin={{{{ top: 10, right: 20, left: 0, bottom: 30 }}}}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="name" axisLine={{false}} tickLine={{false}} tick={{{{ fontSize: 12, fill: "#666" }}}} />
                    <YAxis axisLine={{false}} tickLine={{false}} tick={{{{ fontSize: 12, fill: "#666" }}}} />
                    <ChartTooltip content={{<ChartTooltipContent />}} />
                    <Line type="monotone" dataKey="series1" stroke="#0e68b3" strokeWidth={{3}} dot={{{{ fill: "#0e68b3", strokeWidth: 2, r: 4 }}}} />
                  </LineChart>
                </ChartContainer>
              </div>
            )}}
          </div>
          
          <div className="px-8 pb-6 space-y-4 mt-10">
            {{bulletPoints && bulletPoints.map((point, index) => {{
              const colors = ["bg-teal-600", "bg-yellow-300", "bg-gray-400"];
              const dotColor = colors[index % colors.length];
              return (
                <div key={{index}} className="flex items-start space-x-4">
                  <div className={{`w-6 h-6 ${{dotColor}} rounded-full flex-shrink-0 mt-1`}}></div>
                  <p className="text-base leading-relaxed text-gray-700">{{point}}</p>
                </div>
              );
            }})}}
          </div>
        </div>
      </div>
      <div className="absolute bottom-0 left-0 right-0 h-3 bg-yellow-300"></div>
    </div>
  );
}};

export default {safe_name}StatisticSlide;
'''
        
        file_path = output_path / f"{safe_name}StatisticSlide.tsx"
        file_path.write_text(tsx_content)
        print(f"  ✓ Created: {file_path}")
        return str(file_path)
    
    def _generate_dual_chart_slide(self, data: Dict[str, Any], output_path: Path) -> str:
        """Generate StatisticDualChartSlide.tsx for comparisons."""
        comparisons = data.get("comparisons", {})
        
        bar_data_str = json.dumps(comparisons.get("bar_chart_data", []), indent=6)
        area_data_str = json.dumps(comparisons.get("area_chart_data", []), indent=6)
        
        tsx_content = f'''import React from "react";
import * as z from "zod";
import {{ ImageSchema }} from "../defaultSchemes";
import {{ ChartContainer, ChartTooltip, ChartTooltipContent }} from "@/components/ui/chart";
import {{ BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid }} from "recharts";

export const layoutName = "Financial Comparison";
export const layoutId = "financial-comparison-slide";
export const layoutDescription = "Period-over-period financial comparison";

export const Schema = z.object({{
  sectionTitle: z.string().default("PERIOD COMPARISON"),
  organizationName: z.string().default("Financial Analysis"),
  brandLogo: ImageSchema.default({{
    __image_url__: "https://via.placeholder.com/40x40/14B8A6/FFFFFF?text=FA",
    __image_prompt__: "Financial analytics logo"
  }}),
  barChartData: z.array(z.object({{
    name: z.string(),
    series1: z.number(),
    series2: z.number(),
    series3: z.number(),
  }})).default({bar_data_str}),
  areaChartData: z.array(z.object({{
    name: z.string(),
    series1: z.number(),
    series2: z.number(),
    series3: z.number(),
  }})).default({area_data_str}),
  leftChartTitle: z.string().default("{comparisons.get('period1', 'Previous')} vs {comparisons.get('period2', 'Current')}"),
  leftChartDescription: z.string().default("Period-over-period comparison showing key financial metrics and their changes."),
  rightChartTitle: z.string().default("Cumulative Trend Analysis"),
  rightChartDescription: z.string().default("Progressive financial performance showing cumulative growth and trends over time."),
}});

const chartConfig = {{
  series1: {{ label: "{comparisons.get('period1', 'Period 1')}", color: "#061551" }},
  series2: {{ label: "{comparisons.get('period2', 'Period 2')}", color: "#0e68b3" }},
  series3: {{ label: "Change", color: "#32bbd8" }},
}};

type SchemaType = z.infer<typeof Schema>;

const FinancialComparisonSlide = ({{ data }}: {{ data: Partial<SchemaType> }}) => {{
  const {{ sectionTitle, organizationName, brandLogo, barChartData, areaChartData, leftChartTitle, leftChartDescription, rightChartTitle, rightChartDescription }} = data;

  return (
    <div className="aspect-video max-w-[1280px] w-full bg-white relative overflow-hidden">
      <div className="h-20 bg-teal-600 px-16 py-4 flex justify-between items-center">
        {{sectionTitle && <h1 className="text-4xl font-black text-white">{{sectionTitle}}</h1>}}
        <div className="flex items-center space-x-3">
          {{brandLogo?.__image_url__ && <div className="w-8 h-8"><img src={{brandLogo.__image_url__}} alt={{brandLogo.__image_prompt__}} className="w-full h-full object-contain" /></div>}}
          {{organizationName && <span className="text-lg font-bold text-white">{{organizationName}}</span>}}
        </div>
      </div>

      <div className="flex-1 h-[calc(100%-80px)] flex">
        <div className="w-1/2 p-8 bg-gray-50 flex flex-col">
          <div className="flex items-center justify-start mb-4 space-x-4">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-teal-600 rounded-full"></div>
              <span className="text-sm text-gray-600">{{chartConfig.series1.label}}</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-400 rounded-full"></div>
              <span className="text-sm text-gray-600">{{chartConfig.series2.label}}</span>
            </div>
          </div>

          {{barChartData && barChartData.length > 0 && (
            <div className="flex-1 mb-6">
              <ChartContainer config={{chartConfig}} className="h-full w-full">
                <BarChart data={{barChartData}} margin={{{{ top: 10, right: 20, left: 0, bottom: 30 }}}} barCategoryGap="20%">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" axisLine={{false}} tickLine={{false}} tick={{{{ fontSize: 12, fill: "#666" }}}} />
                  <YAxis axisLine={{false}} tickLine={{false}} tick={{{{ fontSize: 12, fill: "#666" }}}} />
                  <ChartTooltip content={{<ChartTooltipContent />}} />
                  <Bar dataKey="series1" fill="#061551" radius={{[2, 2, 0, 0]}} barSize={{15}} />
                  <Bar dataKey="series2" fill="#0e68b3" radius={{[2, 2, 0, 0]}} barSize={{15}} />
                </BarChart>
              </ChartContainer>
            </div>
          )}}

          <div className="space-y-3">
            {{leftChartTitle && <h3 className="text-xl font-bold text-gray-900">{{leftChartTitle}}</h3>}}
            {{leftChartDescription && <p className="text-base leading-relaxed text-gray-700">{{leftChartDescription}}</p>}}
          </div>
        </div>

        <div className="w-1/2 p-8 bg-white flex flex-col">
          <div className="flex items-center justify-end mb-4 space-x-4">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-teal-600 rounded-full"></div>
              <span className="text-sm text-gray-600">Trend</span>
            </div>
          </div>

          {{areaChartData && areaChartData.length > 0 && (
            <div className="flex-1 mb-6">
              <ChartContainer config={{chartConfig}} className="h-full w-full">
                <AreaChart data={{areaChartData}} margin={{{{ top: 10, right: 20, left: 0, bottom: 30 }}}}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" axisLine={{false}} tickLine={{false}} tick={{{{ fontSize: 12, fill: "#666" }}}} />
                  <YAxis axisLine={{false}} tickLine={{false}} tick={{{{ fontSize: 12, fill: "#666" }}}} />
                  <ChartTooltip content={{<ChartTooltipContent />}} />
                  <Area type="monotone" dataKey="series1" stackId="1" stroke="#061551" fill="#061551" fillOpacity={{0.8}} />
                  <Area type="monotone" dataKey="series2" stackId="1" stroke="#0e68b3" fill="#0e68b3" fillOpacity={{0.8}} />
                </AreaChart>
              </ChartContainer>
            </div>
          )}}

          <div className="space-y-3">
            {{rightChartTitle && <h3 className="text-xl font-bold text-gray-900">{{rightChartTitle}}</h3>}}
            {{rightChartDescription && <p className="text-base leading-relaxed text-gray-700">{{rightChartDescription}}</p>}}
          </div>
        </div>
      </div>
    </div>
  );
}};

export default FinancialComparisonSlide;
'''
        
        file_path = output_path / "FinancialComparisonSlide.tsx"
        file_path.write_text(tsx_content)
        print(f"  ✓ Created: {file_path}")
        return str(file_path)


def main():
    """Main entry point."""
    print("=" * 80)
    print("🎨 Professional TSX Financial Slide Generator".center(80))
    print("=" * 80)
    print()
    
    # Your financial data
    financial_text = """ Executive Summary
(a) Full Period (May 2019 - Aug 2025):
* Gross Profit, EBITDA, and Net Income peaked in December 2020 ($101,828, $72,091, $72,091) before declining sharply.
* Customer Collection Days fluctuated widely, peaking in Jan 2024 (66,021 days).
* Inventory Days showed extreme volatility, with a high in Jan 2024 (612,370 days).
* Supplier Payment Days turned positive in Sep 2024 (22,309 days) after negative values.
* Cash flow stability is inconsistent, with operating cash flow heavily dependent on income.
(b) Selected Period VS Comparison Period (Aug 2024 VS Sep 2024):
* Income fell from $9,384 to $5,200.
* Gross Profit declined by 45.6%.
* EBITDA and Net Income dropped by 53.1%.
* Customer Collection Days increased by 86.2%.
* Inventory Days decreased by 90.3%.
* Supplier Payment Days shifted from -4,468 to 22,309 days.
* Operating cash flow weakened due to lower income.
Income
* Trend Analysis: Income shows significant volatility, with the highest peak in December 2020 ($155,815) and a sharp decline post-April 2021, stabilizing at minimal values until mid-2024. The average income across the dataset is approximately $15,000, with outliers like December 2020 and July 2024 ($12,186).
* Period-over-Period Analysis: Sep 2024 recorded $5,200, while Aug 2024 was $9,384, an absolute decrease of $4,184 (-44.6%). The average across both periods was $7,292, indicating a downward trend.
* Reason: Sep 2024’s income was driven by invoices from Customer E ($4,000) and Customer AR ($1,200). Aug 2024’s higher value included a large invoice from Quantum computer Inc ($10,300).
Cost of Sales
* Trend Analysis: Cost of Sales mirrors Income trends, peaking in December 2020 ($53,987) and dropping sharply post-April 2021. The average is around $10,000, with outliers like December 2020 and July 2024 ($1).
* Period-over-Period Analysis: Sep 2024 recorded $103, while Aug 2024 was $10, an absolute increase of $93 (+930%). The average across both periods was $56.50, indicating an upward trend.
* Reason: Sep 2024’s increase was due to a single invoice from V ($98).
Expenses
* Trend Analysis: Expenses peaked in December 2020 ($29,947) and declined post-2021, with minimal activity in 2024. The average is approximately $5,000, with outliers like December 2020.
* Period-over-Period Analysis: Sep 2024 recorded $0, while Aug 2024 was -$500, an absolute decrease of $500 (-100%). The average across both periods was -$250, indicating a downward trend.
* Reason: Aug 2024’s negative value reflects a credit note or adjustment in the "Technology & Content" category.
Gross Profit
* Trend Analysis: The overall trend shows growth from May 2019 ($8,321) to December 2020 ($101,828), followed by a sharp decline. The peak was in December 2020 ($101,828), and the lowest point was in December 2021 ($0). The dataset-wide average is $10,743.
* Period-over-Period Analysis: Sep 2024 ($5,097) vs Aug 2024 ($9,374) shows a downward trend, with a 45.6% decrease.
* Reason: Income dropped from $9,384 in Aug 2024 to $5,200 in Sep 2024, while Cost of Sales increased from $10 to $103.
EBITDA
* Trend Analysis: The trend mirrors Gross Profit, peaking in December 2020 ($72,091) and hitting the lowest in December 2021 ($0). The average is $6,521.
* Period-over-Period Analysis: Sep 2024 ($5,097) vs Aug 2024 ($10,874) shows a 53.1% decline.
* Reason: Income reduction and a $500 expense reversal in Aug 2024 (Technology & Content) contributed to the drop.
Net Income
* Trend Analysis: Identical to EBITDA trends, with the same peak ($72,091) and low ($0). The average is $6,521.
* Period-over-Period Analysis: Sep 2024 ($5,097) vs Aug 2024 ($10,874) reflects a 53.1% decrease.
Customer Collection Days
* Trend Analysis: Data starts from Oct 2023, peaking in Jan 2024 (66,021 days) and lowest in Jun 2024 (-17,233 days). The average is 11,542 days.
* Period-over-Period Analysis: Sep 2024 (1,471 days) vs Aug 2024 (790 days) shows a 86.2% increase.
Inventory Days
* Trend Analysis: Peaked in Jan 2024 (612,370 days) and lowest in Jun 2024 (-612,340 days). The average is 102,061 days.
* Period-over-Period Analysis: Sep 2024 (5,944 days) vs Aug 2024 (61,234 days) shows a 90.3% decline.
Supplier Payment Days
* Trend Analysis: Data starts from Oct 2023, peaking in Sep 2024 (22,309 days) and lowest in Aug 2024 (-4,468 days). The average is 1,487 days.
* Period-over-Period Analysis: Sep 2024 (22,309 days) vs Aug 2024 (-4,468 days) shows a significant shift from negative to positive.
CashFlow Analysis
* Operating Activities: Income dropped from $9,384 (Aug 2024) to $5,200 (Sep 2024), while expenses remained stable.
* Investing & Financing Activities: No data for these categories.
* Liquidity: Operating cash flow weakened in Sep 2024 due to lower income.
"""
    
    generator = FinancialTSXGenerator()
    
    try:
        files = generator.generate_financial_slides(
            financial_text=financial_text,
            output_dir="generated_financial_slides"
        )
        
        print("\n" + "=" * 80)
        print("✅ TSX Slides Generated Successfully!".center(80))
        print("=" * 80)
        print(f"\n📁 Output Directory: generated_financial_slides/")
        print(f"\n📄 Generated Files:")
        for file in files:
            print(f"   • {Path(file).name}")
        print("\n💡 These TSX components are ready to use in your React/Next.js project!")
        print("   Copy them to your slides directory and import them in your presentation.")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
