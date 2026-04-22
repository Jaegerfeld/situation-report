# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       17.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Implementiert die Flow Time / Cycle Time Metrik mit zwei Berechnungsmethoden:
#   Methode A: Kalendertage (First Date → Closed Date).
#   Methode B: Summe der Stage-Minuten von der ersten bis zur letzten Stage
#              (ausschließlich der Closed-Stage) geteilt durch 1440.
#   Stellt zwei Diagramme bereit: horizontaler Boxplot mit Statistik-Header
#   und Scatterplot mit LOESS-Trendlinie sowie Median-, 85.- und 95.-Perzentil-
#   Referenzlinien. Issues ohne First Date oder Closed Date sowie Issues mit
#   Cycle Time = 0 werden ausgeschlossen.
# =============================================================================

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime

import plotly.graph_objects as go

from ..loader import IssueRecord, ReportData
from ..terminology import FLOW_TIME, term
from . import register
from .base import MetricPlugin, MetricResult

CT_METHOD_A = "A"
CT_METHOD_B = "B"

# Abbreviated month names for x-axis tick labels (German, index 1–12).
_MONTH_ABBR = ["", "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
               "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


@dataclass
class _FlowTimePoint:
    """Single data point for cycle time computation."""
    key: str
    closed_date: datetime
    cycle_days: float


# ---------------------------------------------------------------------------
# Pure helper functions (testable without a running display)
# ---------------------------------------------------------------------------

def _loess(x_num: list[float], y: list[float], frac: float = 0.4) -> list[float]:
    """
    Compute LOESS-smoothed y values using local weighted linear regression.

    Implements the LOESS (Locally Weighted Scatterplot Smoothing) algorithm
    with tricube weighting. No external dependencies required.

    Args:
        x_num: Numeric x values (need not be sorted).
        y:     Corresponding y values. Must have the same length as x_num.
        frac:  Fraction of points used for each local fit (bandwidth).
               Higher values produce a smoother curve. Default 0.4.

    Returns:
        Smoothed y values at the same x positions and in the same order as
        the input. Returns a plain copy when fewer than 3 points are given.
    """
    n = len(x_num)
    if n < 3:
        return list(y)
    k = min(max(3, int(frac * n)), n)
    result: list[float] = []
    for i in range(n):
        xi = x_num[i]
        # k nearest neighbours by x distance
        idx = sorted(range(n), key=lambda j: abs(x_num[j] - xi))[:k]
        max_d = max(abs(x_num[j] - xi) for j in idx)
        if max_d == 0:
            result.append(sum(y[j] for j in idx) / k)
            continue
        # Tricube weights: (1 − (|x_j − x_i| / max_d)³)³
        w = [(1 - (abs(x_num[j] - xi) / max_d) ** 3) ** 3 for j in idx]
        xk = [x_num[j] for j in idx]
        yk = [y[j] for j in idx]
        sw = sum(w)
        swx = sum(w[l] * xk[l] for l in range(k))
        swy = sum(w[l] * yk[l] for l in range(k))
        swxx = sum(w[l] * xk[l] ** 2 for l in range(k))
        swxy = sum(w[l] * xk[l] * yk[l] for l in range(k))
        denom = sw * swxx - swx ** 2
        if abs(denom) < 1e-10:
            result.append(swy / sw)
        else:
            slope = (sw * swxy - swx * swy) / denom
            intercept = (swy - slope * swx) / sw
            result.append(intercept + slope * xi)
    return result


def _month_ticks(dates: list[datetime]) -> tuple[list[str], list[str]]:
    """
    Generate monthly tick positions and labels for the scatterplot x-axis.

    Odd months receive an abbreviated name (e.g. "Jan", "Mär"); January also
    shows the year ("Jan 2025"). Even months receive a small dot marker "·".
    One month of padding is added beyond the last data point.

    Args:
        dates: List of datetime values from scatter data.

    Returns:
        Tuple of (tickvals, ticktext) suitable for plotly xaxis configuration.
        tickvals are ISO date strings ("YYYY-MM-DD"), ticktext are labels.
    """
    if not dates:
        return [], []

    min_d = min(dates)
    max_d = max(dates)

    # End one month after the last data point for visual padding
    end_month = max_d.month + 1
    end_year = max_d.year
    if end_month > 12:
        end_month = 1
        end_year += 1

    tickvals: list[str] = []
    ticktext: list[str] = []
    year, month = min_d.year, min_d.month

    while (year, month) <= (end_year, end_month):
        tickvals.append(f"{year:04d}-{month:02d}-01")
        if month % 2 == 1:  # odd month → name label
            label = f"Jan {year}" if month == 1 else _MONTH_ABBR[month]
        else:              # even month → small dot
            label = "·"
        ticktext.append(label)
        month += 1
        if month > 12:
            month = 1
            year += 1

    return tickvals, ticktext


def _point_color(cycle_days: float, pct85: float, pct95: float) -> str:
    """
    Return the marker color for a single scatter point based on its percentile.

    Points at or above the 95th percentile are colored red (outlier warning).
    Points at or above the 85th percentile (but below 95th) are colored orange.
    All other points are steelblue.

    Args:
        cycle_days: Cycle time value of the point.
        pct85:      85th percentile threshold from the current dataset.
        pct95:      95th percentile threshold from the current dataset.

    Returns:
        CSS color string: "red", "orange", or "steelblue".
    """
    if cycle_days >= pct95:
        return "red"
    if cycle_days >= pct85:
        return "orange"
    return "steelblue"


def _compute_stats(values: list[float]) -> dict:
    """
    Compute descriptive statistics for a list of cycle time values.

    Args:
        values: List of cycle time values in days (must not be empty).

    Returns:
        Dict with keys: min, q1, mean, median, q3, max, pct85, pct90, pct95,
        sd, cv. pct90 is the percentage of issues completed within 90 days (SLE).
    """
    sorted_v = sorted(values)
    n = len(sorted_v)
    q1 = sorted_v[n // 4]
    q3 = sorted_v[(3 * n) // 4]
    mean = statistics.mean(sorted_v)
    med = statistics.median(sorted_v)
    sd = statistics.stdev(sorted_v) if n > 1 else 0.0
    cv = (sd / mean * 100) if mean else 0.0
    pct85 = sorted_v[min(int(n * 0.85), n - 1)]
    pct95 = sorted_v[min(int(n * 0.95), n - 1)]
    # Percentage of issues completed within 90 days (SLE: how many % are under the threshold)
    pct90 = round(sum(1 for v in sorted_v if v <= 90) / n * 100, 1)
    return dict(
        min=sorted_v[0], q1=q1, mean=mean, median=med,
        q3=q3, max=sorted_v[-1],
        pct85=pct85, pct90=pct90, pct95=pct95,
        sd=sd, cv=cv,
    )


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
            MetricResult with stats (min/q1/mean/median/q3/max/pct85/pct90/
            pct95/sd/cv/count/zero_day_count/ct_method) and chart_data as
            list of _FlowTimePoint.
        """
        points: list[_FlowTimePoint] = []
        zero_day_count = 0
        zero_day_records: list = []
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
                zero_day_records.append(issue)
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
                stats={
                    "zero_day_count": zero_day_count,
                    "zero_day_records": zero_day_records,
                    "ct_method": self.ct_method,
                },
                warnings=warnings,
            )

        values = [p.cycle_days for p in points]
        stats = _compute_stats(values)
        stats["count"] = len(points)
        stats["zero_day_count"] = zero_day_count
        stats["zero_day_records"] = zero_day_records
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

        The scatterplot includes a LOESS trendline and dotted reference lines
        for the median (red), 85th percentile (light green), and 95th percentile
        (cyan). The x-axis uses custom month ticks: odd months show an
        abbreviated name, even months show a small dot marker.

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
            fillcolor="orange",
            line_color="darkgray",
            boxpoints="outliers",
            marker=dict(color="red", size=6),
            text=[p.key for p in points],
            hovertemplate="<b>%{text}</b><br>Days: %{x}<extra></extra>",
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

        # --- Scatterplot ---
        # Sort chronologically for LOESS and x-axis display
        sorted_pts = sorted(points, key=lambda p: p.closed_date)
        sorted_dates = [p.closed_date for p in sorted_pts]
        sorted_values = [p.cycle_days for p in sorted_pts]
        all_dates = [p.closed_date for p in points]
        all_keys = [p.key for p in points]

        # LOESS trendline
        epoch = sorted_dates[0]
        x_num = [(d - epoch).total_seconds() / 86400 for d in sorted_dates]
        loess_y = _loess(x_num, sorted_values)

        # Month tick labels
        tickvals, ticktext = _month_ticks(sorted_dates)

        fig_scatter = go.Figure()

        # Scatter points — colour-coded by percentile
        point_colors = [
            _point_color(p.cycle_days, s["pct85"], s["pct95"]) for p in points
        ]
        fig_scatter.add_trace(go.Scatter(
            x=all_dates,
            y=values,
            mode="markers",
            marker=dict(color=point_colors, size=5, opacity=0.7),
            text=all_keys,
            hovertemplate="<b>%{text}</b><br>Closed: %{x}<br>Days: %{y}<extra></extra>",
            name=label,
        ))

        # LOESS trendline (blue, solid)
        fig_scatter.add_trace(go.Scatter(
            x=sorted_dates,
            y=loess_y,
            mode="lines",
            line=dict(color="blue", width=2),
            name="Trend (LOESS)",
        ))

        # Reference lines (dotted)
        ref_lines = [
            (s["median"],  "red",        f"Median: {round(s['median'], 1)}"),
            (s["pct85"],   "lightgreen", f"85th %: {round(s['pct85'], 1)}"),
            (s["pct95"],   "cyan",       f"95th %: {round(s['pct95'], 1)}"),
        ]
        for y_val, color, annotation in ref_lines:
            fig_scatter.add_hline(
                y=y_val,
                line_color=color,
                line_dash="dot",
                line_width=2,
                annotation_text=annotation,
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
            xaxis=dict(
                tickmode="array",
                tickvals=tickvals,
                ticktext=ticktext,
            ),
        )

        return [fig_box, fig_scatter]


register(FlowTimeMetric())
