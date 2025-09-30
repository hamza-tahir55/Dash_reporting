"""
Financial data models for report generation.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


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
