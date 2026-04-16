# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       16.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Implementiert die Flow Time / Cycle Time Metrik mit zwei Berechnungsmethoden:
#   Methode A: Kalendertage (First Date → Closed Date).
#   Methode B: Summe der Stage-Minuten von der ersten bis zur letzten Stage
#              (ausschließlich der Closed-Stage) geteilt durch 1440.
#   Stellt zwei Diagramme bereit: horizontaler Boxplot mit Statistik-Header
#   und Scatterplot mit Trendlinie. Issues ohne First Date oder Closed Date
#   sowie Issues mit Cycle Time = 0 werden ausgeschlossen.
# =============================================================================

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..loader import IssueRecord, ReportData
from ..terminology import FLOW_TIME, term
from . import register
from .base import MetricPlugin, MetricResult

CT_METHOD_A = "A"
CT_METHOD_B = "B"


@dataclass
class _FlowTimePoint:
    """Single data point for cycle time computation."""
    key: str
    closed_date: datetime
    cycle_days: float


def _compute_stats(values: list[float]) -> dict:
    """
    Compute descriptive statistics for a list of cycle time values.

    Args:
        values: List of cycle time values in days (must not be empty).

    Returns:
        Dict with keys: min, q1, mean, median, q3, max, pct90, sd, cv.
    """
    sorted_v = sorted(values)
    n = len(sorted_v)
    q1 = sorted_v[n // 4]
    q3 = sorted_v[(3 * n) // 4]
    mean = statistics.mean(sorted_v)
    med = statistics.median(sorted_v)
    sd = statistics.stdev(sorted_v) if n > 1 else 0.0
    cv = (sd / mean * 100) if mean else 0.0
    pct90 = sorted_v[int(n * 0.9)]
    return dict(min=sorted_v[0], q1=q1, mean=mean, median=med,
                q3=q3, max=sorted_v[-1], pct90=pct90, sd=sd, cv=cv)


class FlowTimeMetric(MetricPlugin):
    """
    Flow Time / Cycle Time metric.

    Supports two calculation methods:
    - Method A (default): calendar days from First Date to Closed Date.
    - Method B: sum of stage minutes (all stages except the last/Closed stage)
      divided by 1440, reflecting active processing time only.

    Set ct_method = CT_METHOD_A or CT_METHOD_B before calling compute().
    """

    metric_id = FLOW_TIME
    ct_method: str = CT_METHOD_A

    def _cycle_days_method_b(self, issue: IssueRecord, stages: list[str]) -> float:
        """
        Compute cycle time via Method B: sum of stage minutes excluding the last stage.

        Args:
            issue:  IssueRecord with stage_minutes populated.
            stages: Ordered list of workflow stages from ReportData.

        Returns:
            Cycle time in days (float), or 0.0 if no relevant stage data.
        """
        stages_to_sum = stages[:-1] if len(stages) > 1 else stages
        minutes = sum(issue.stage_minutes.get(s, 0) for s in stages_to_sum)
        return round(minutes / 1440, 2)

    def compute(self, data: ReportData, terminology: str) -> MetricResult:
        """
        Compute cycle time in days for all eligible issues.

        Only issues with both First Date and Closed Date are considered.
        Issues with cycle time <= 0 are excluded and counted as zero_day_count.

        Args:
            data:        Filtered ReportData from loader.py.
            terminology: Active terminology mode (SAFe or Global).

        Returns:
            MetricResult with stats (min/q1/mean/median/q3/max/pct90/sd/cv/count/
            zero_day_count/ct_method) and chart_data as list of _FlowTimePoint.
        """
        points: list[_FlowTimePoint] = []
        zero_day_count = 0
        warnings: list[str] = []

        for issue in data.issues:
            if issue.first_date is None or issue.closed_date is None:
                continue

            if self.ct_method == CT_METHOD_B:
                delta = self._cycle_days_method_b(issue, data.stages)
            else:
                delta = (issue.closed_date - issue.first_date).total_seconds() / 86400
                delta = round(delta, 2)

            if delta <= 0:
                zero_day_count += 1
                continue
            points.append(_FlowTimePoint(
                key=issue.key,
                closed_date=issue.closed_date,
                cycle_days=delta,
            ))

        if not points:
            warnings.append("No issues with valid First Date and Closed Date found.")
            return MetricResult(
                metric_id=self.metric_id,
                stats={"zero_day_count": zero_day_count, "ct_method": self.ct_method},
                warnings=warnings,
            )

        values = [p.cycle_days for p in points]
        stats = _compute_stats(values)
        stats["count"] = len(points)
        stats["zero_day_count"] = zero_day_count
        stats["ct_method"] = self.ct_method

        return MetricResult(
            metric_id=self.metric_id,
            stats=stats,
            chart_data=points,
            warnings=warnings,
        )

    def render(self, result: MetricResult, terminology: str) -> list[go.Figure]:
        """
        Render a boxplot and a scatterplot for the Flow Time metric.

        Args:
            result:      MetricResult from compute().
            terminology: Active terminology mode for axis/title labels.

        Returns:
            List of two plotly Figures: [boxplot, scatterplot].
            Empty list if result contains no chart data.
        """
        if not result.chart_data:
            return []

        points: list[_FlowTimePoint] = result.chart_data
        s = result.stats
        label = term(FLOW_TIME, terminology)
        method_label = f"Methode {s.get('ct_method', CT_METHOD_A)}"

        header = (
            f"{label} ({method_label})  "
            f"Min: {s['min']} | Q1: {s['q1']} | Mean: {round(s['mean'], 2)} | "
            f"Median: {s['median']} | Q3: {s['q3']} | Max: {s['max']} | "
            f"#Items: {s['count']} | 90d CT%: {s['pct90']} | "
            f"SD: {round(s['sd'], 2)} | SD%(CV): {round(s['cv'], 2)} | "
            f"Zero Day Issues removed: {s['zero_day_count']}"
        )

        values = [p.cycle_days for p in points]

        # --- Boxplot ---
        fig_box = go.Figure()
        fig_box.add_trace(go.Box(
            x=values,
            orientation="h",
            marker_color="orange",
            line_color="darkgray",
            boxpoints="outliers",
            marker=dict(color="red", size=6),
            name=label,
        ))
        fig_box.update_layout(
            title=header,
            title_font_size=11,
            xaxis_title="CycleDays",
            plot_bgcolor="#e8e8e8",
            paper_bgcolor="#e8e8e8",
            showlegend=False,
            height=400,
        )

        # --- Scatterplot with trend line ---
        dates = [p.closed_date for p in points]
        keys = [p.key for p in points]

        # Simple linear trend via index
        n = len(values)
        x_idx = list(range(n))
        slope = (sum(i * v for i, v in zip(x_idx, values)) - n * statistics.mean(x_idx) * statistics.mean(values)) / (
            sum(i ** 2 for i in x_idx) - n * statistics.mean(x_idx) ** 2
        ) if n > 1 else 0
        intercept = statistics.mean(values) - slope * statistics.mean(x_idx)
        trend = [intercept + slope * i for i in x_idx]

        fig_scatter = go.Figure()
        fig_scatter.add_trace(go.Scatter(
            x=dates, y=values, mode="markers",
            marker=dict(color="steelblue", size=5, opacity=0.6),
            text=keys,
            hovertemplate="<b>%{text}</b><br>Closed: %{x}<br>Days: %{y}<extra></extra>",
            name=label,
        ))
        fig_scatter.add_trace(go.Scatter(
            x=dates, y=trend, mode="lines",
            line=dict(color="royalblue", width=2),
            name="Trend",
        ))
        # Reference lines
        for y_val, color, dash, lbl in [
            (s["median"], "cyan", "dash", "Median"),
            (s["mean"], "red", "dot", "Mean"),
            (s["pct90"], "green", "dashdot", "90th %"),
        ]:
            fig_scatter.add_hline(
                y=y_val, line_color=color, line_dash=dash,
                annotation_text=f"{lbl}: {round(y_val, 1)}",
                annotation_position="right",
            )
        fig_scatter.update_layout(
            title=header,
            title_font_size=11,
            xaxis_title="Date",
            yaxis_title="CycleDays",
            plot_bgcolor="#e8e8e8",
            paper_bgcolor="#e8e8e8",
            height=500,
        )

        return [fig_box, fig_scatter]


register(FlowTimeMetric())
