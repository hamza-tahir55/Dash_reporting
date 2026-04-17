"""
Financial data models for report generation.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ── Legacy models (kept for backward compatibility) ──────────────────────────

class FinancialMetric(BaseModel):
    date: str
    value: float
    label: Optional[str] = None


class TrendAnalysis(BaseModel):
    metric_name: str
    description: str
    peak_value: Optional[float] = None
    peak_date: Optional[str] = None
    lowest_value: Optional[float] = None
    lowest_date: Optional[str] = None
    average: Optional[float] = None
    data_points: List[FinancialMetric] = Field(default_factory=list)


class PeriodComparison(BaseModel):
    metric_name: str
    current_period: str
    current_value: float
    comparison_period: str
    comparison_value: float
    absolute_change: float
    percentage_change: float
    reason: Optional[str] = None


class ExecutiveSummary(BaseModel):
    full_period_summary: List[str]
    comparison_summary: List[str]
    period_label: str = "Full Period"
    comparison_label: str = "Period Comparison"


class FinancialReportData(BaseModel):
    title: str = "Financial Analysis Report"
    report_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    executive_summary: ExecutiveSummary
    trend_analyses: List[TrendAnalysis] = Field(default_factory=list)
    period_comparisons: List[PeriodComparison] = Field(default_factory=list)
    additional_notes: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


# ── New frontend-contract models ──────────────────────────────────────────────

class ChartData(BaseModel):
    labels: List[str]
    values: List[float]
    chart_type: str  # "bar" or "line"
    cp_values: Optional[List[float]] = None  # comparison period values
    cp_label: Optional[str] = None           # comparison period label (e.g. "Dec 25")
    tp_label: Optional[str] = None           # target/selected period label (e.g. "Jan 26")


class RootCauseInput(BaseModel):
    name: str
    chart_data: ChartData


class SlideInput(BaseModel):
    kpi_name: str
    chart_data: ChartData
    root_causes: List[RootCauseInput] = []


class GenerateContentRequest(BaseModel):
    financial_text: str
    selected_slides: List[SlideInput]


class RootCauseOutput(BaseModel):
    name: str
    description: str
    bullet_points: List[str]
    chart_data: ChartData


class SlideOutput(BaseModel):
    kpi_name: str
    title: str
    description: str
    bullet_points: List[str]
    root_causes: List[RootCauseOutput] = []


class GenerateContentResponse(BaseModel):
    slides: List[SlideOutput]


class RootCauseSlide(BaseModel):
    name: str
    description: str
    bullet_points: List[str]
    chart_data: Optional[ChartData] = None


class SlidePayload(BaseModel):
    kpi_name: str
    title: str
    description: str
    bullet_points: List[str]
    chart_data: Optional[ChartData] = None
    root_causes: List[RootCauseSlide] = []


class GeneratePDFRequest(BaseModel):
    financial_text: str
    report_title: str
    report_subtitle: Optional[str] = ""
    contact_email: Optional[str] = ""
    contact_website: Optional[str] = ""
    organization_name: Optional[str] = ""
    contact_phone: Optional[str] = ""
    prepared_by: Optional[str] = ""
    presentation_date: Optional[str] = ""
    dash_logo: bool = True
    company_name: Optional[str] = ""
    logo_url: Optional[str] = ""
    slides: List[SlidePayload]


class GeneratePDFResponse(BaseModel):
    pdf_url: str
