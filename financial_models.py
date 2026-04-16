"""
Financial data models for report generation.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ---------------------------------------------------------------------------
# New models for the KPI-selection / slide-content flow
# ---------------------------------------------------------------------------

class ChartDataPoint(BaseModel):
    """Chart data sent from the frontend (from Xero API)."""
    labels: List[str] = []
    values: List[float] = []
    chart_type: Optional[str] = "bar"   # bar | line | pie | doughnut


class RootCauseSelection(BaseModel):
    """A single root-cause section the user selected for a KPI."""
    name: str                                    # e.g. "Top Customers by Value Spend"
    chart_data: Optional[ChartDataPoint] = None  # Chart data from the frontend


class KPISlideSelection(BaseModel):
    """One KPI the user selected, with its chosen root causes."""
    kpi_name: str                                       # e.g. "Income"
    root_causes: List[RootCauseSelection] = []
    chart_data: Optional[ChartDataPoint] = None         # KPI-level time-series (from Xero)


class GenerateSlideContentRequest(BaseModel):
    """Request body for POST /generate-slide-content."""
    financial_text: str                                 # The AI summary already generated
    selected_slides: List[KPISlideSelection]


class RootCauseContent(BaseModel):
    """AI-generated content for a single root cause, returned to the frontend."""
    name: str
    description: str
    bullet_points: List[str] = []
    chart_data: Optional[ChartDataPoint] = None         # Passed through unchanged


class SlideContent(BaseModel):
    """AI-generated content for a single KPI slide (editable by the user)."""
    kpi_name: str
    title: str
    description: str
    bullet_points: List[str] = []
    root_causes: List[RootCauseContent] = []
    chart_data: Optional[ChartDataPoint] = None  # KPI-level time-series chart data


class GenerateSlideContentResponse(BaseModel):
    """Response body for POST /generate-slide-content."""
    slides: List[SlideContent]


class FinancialMetric(BaseModel):
    """Represents a single financial metric data point."""
    date: str
    value: float
    label: Optional[str] = None


class TrendAnalysis(BaseModel):
    """Trend analysis for a metric."""
    metric_name: str
    description: str
    peak_value: Optional[float] = None
    peak_date: Optional[str] = None
    lowest_value: Optional[float] = None
    lowest_date: Optional[str] = None
    average: Optional[float] = None
    data_points: List[FinancialMetric] = Field(default_factory=list)


class PeriodComparison(BaseModel):
    """Period-over-period comparison."""
    metric_name: str
    current_period: str
    current_value: float
    comparison_period: str
    comparison_value: float
    absolute_change: float
    percentage_change: float
    reason: Optional[str] = None


class ExecutiveSummary(BaseModel):
    """Executive summary section."""
    full_period_summary: List[str]
    comparison_summary: List[str]
    period_label: str = "Full Period"
    comparison_label: str = "Period Comparison"


class FinancialReportData(BaseModel):
    """Complete financial report data structure."""
    title: str = "Financial Analysis Report"
    report_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    executive_summary: ExecutiveSummary
    trend_analyses: List[TrendAnalysis] = Field(default_factory=list)
    period_comparisons: List[PeriodComparison] = Field(default_factory=list)
    additional_notes: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
