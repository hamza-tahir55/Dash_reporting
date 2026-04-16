"""
AI commentary generation for financial KPI slides.
Fires all DeepSeek calls in parallel via ThreadPoolExecutor.
"""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional

from openai_service import AIService
from financial_models import (
    SlideInput,
    SlideOutput,
    RootCauseOutput,
    RootCauseInput,
    ChartData,
)


def _compute_trend(values: List[float]) -> str:
    if len(values) < 2:
        return "flat"
    delta = values[-1] - values[0]
    pct = (delta / values[0] * 100) if values[0] != 0 else 0
    if pct > 3:
        return "up"
    if pct < -3:
        return "down"
    return "flat"


def _pct_change(values: List[float]) -> float:
    if len(values) < 2 or values[0] == 0:
        return 0.0
    return round((values[-1] - values[0]) / abs(values[0]) * 100, 1)


def _generate_kpi_commentary(
    ai: AIService,
    financial_text: str,
    kpi_name: str,
    labels: List[str],
    values: List[float],
) -> dict:
    """Call DeepSeek to generate title, description, and bullet_points for one KPI."""
    trend = _compute_trend(values)
    pct = _pct_change(values)
    latest = values[-1] if values else 0

    prompt = f"""You are a financial analyst. Given the following financial performance data for \
{kpi_name}, write a professional slide description.

Context from financial report:
{financial_text[:2000]}

KPI Data ({kpi_name}):
- Time periods: {labels}
- Values: {values}
- Trend: {trend}
- Latest value: {latest:,.0f}
- Change from first to last: {pct}%

Return valid JSON only (no markdown):
{{
  "title": "concise 4-6 word title for this KPI slide",
  "description": "2-3 sentence professional analysis of the trend and what it means",
  "bullet_points": ["3 specific data-driven insights, each under 15 words", "insight 2", "insight 3"]
}}"""

    raw = ai.generate_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        json_mode=True,
    )
    return json.loads(raw)


def _generate_rc_commentary(
    ai: AIService,
    financial_text: str,
    kpi_name: str,
    rc_name: str,
    labels: List[str],
    values: List[float],
) -> dict:
    """Call DeepSeek to generate description and bullet_points for one root cause."""
    trend = _compute_trend(values)
    pct = _pct_change(values)
    latest = values[-1] if values else 0

    prompt = f"""You are a financial analyst examining a root cause driver for {kpi_name}.

Context from financial report:
{financial_text[:2000]}

Root Cause Metric ({rc_name}):
- Time periods: {labels}
- Values: {values}
- Trend: {trend}
- Latest value: {latest:,.0f}
- Change from first to last: {pct}%

Return valid JSON only (no markdown):
{{
  "description": "2-3 sentence professional analysis of this driver and its impact on {kpi_name}",
  "bullet_points": ["2-3 specific data-driven insights, each under 15 words", "insight 2"]
}}"""

    raw = ai.generate_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        json_mode=True,
    )
    return json.loads(raw)


def generate_slide_commentary(
    financial_text: str,
    slides_input: List[SlideInput],
) -> List[SlideOutput]:
    """
    Generate AI commentary for all slides in parallel.

    Fires one DeepSeek task per KPI and one per root cause, all concurrent
    via ThreadPoolExecutor(max_workers=5).

    Returns a list of SlideOutput in the same order as slides_input.
    """
    ai = AIService()

    # Build flat task list: (slide_idx, rc_idx_or_None)
    # rc_idx None → KPI-level task; int → root-cause task
    tasks: List[Tuple[int, Optional[int]]] = []
    for i, slide in enumerate(slides_input):
        tasks.append((i, None))
        for j in range(len(slide.root_causes)):
            tasks.append((i, j))

    # Keyed results: (slide_idx, rc_idx_or_None) → dict
    results: dict = {}

    def run_task(slide_idx: int, rc_idx: Optional[int]) -> Tuple[Tuple, dict]:
        slide = slides_input[slide_idx]
        if rc_idx is None:
            data = _generate_kpi_commentary(
                ai,
                financial_text,
                slide.kpi_name,
                slide.chart_data.labels,
                slide.chart_data.values,
            )
        else:
            rc = slide.root_causes[rc_idx]
            data = _generate_rc_commentary(
                ai,
                financial_text,
                slide.kpi_name,
                rc.name,
                rc.chart_data.labels,
                rc.chart_data.values,
            )
        return (slide_idx, rc_idx), data

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(run_task, si, ri): (si, ri) for si, ri in tasks}
        for future in as_completed(futures):
            key, data = future.result()
            results[key] = data

    # Assemble SlideOutput objects in original order
    outputs: List[SlideOutput] = []
    for i, slide in enumerate(slides_input):
        kpi_result = results[(i, None)]

        rc_outputs: List[RootCauseOutput] = []
        for j, rc in enumerate(slide.root_causes):
            rc_result = results[(i, j)]
            rc_outputs.append(
                RootCauseOutput(
                    name=rc.name,
                    description=rc_result.get("description", ""),
                    bullet_points=rc_result.get("bullet_points", []),
                    chart_data=rc.chart_data,
                )
            )

        outputs.append(
            SlideOutput(
                kpi_name=slide.kpi_name,
                title=kpi_result.get("title", f"{slide.kpi_name} Performance"),
                description=kpi_result.get("description", ""),
                bullet_points=kpi_result.get("bullet_points", []),
                root_causes=rc_outputs,
            )
        )

    return outputs
