# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       17.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Implementiert die Flow Velocity / Throughput Metrik. Zählt abgeschlossene
#   Issues (Closed Date vorhanden) nach Zeitraum. Liefert drei Diagramme:
#   Histogramm (Häufigkeit der täglich abgeschlossenen Items), Liniendiagramm
#   (Items pro Woche über die Zeit) und Balkendiagramm (Items pro PI).
#   PI-Intervalle werden aus einer optionalen JSON-Konfigdatei geladen; ohne
#   Konfigdatei werden Kalenderquartale als Standard-PIs verwendet.
#   Nur Issues mit Closed Date fließen in die Berechnung ein.
# =============================================================================

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass
from datetime import date

import plotly.graph_objects as go

from ..loader import ReportData
from ..pi_config import (
    PIInterval, assign_pi, default_quarter_intervals, load_pi_config,
)
from ..terminology import FLOW_VELOCITY, term
from . import register
from .base import MetricPlugin, MetricResult


def _iso_week_label(d: date) -> str:
    """
    Format a date as a SAFe/ISO PI label: 'YYYY.WW'.

    Args:
        d: Calendar date.

    Returns:
        String like '2025.11'.
    """
    iso = d.isocalendar()
    return f"{iso.year}.{iso.week:02d}"


@dataclass
class _VelocityData:
    """Aggregated velocity data for all three chart variants."""
    daily_freq: dict[int, int]        # items-per-day count -> frequency (histogram)
    weekly: dict[str, int]            # 'YYYY.WW' -> item count
    per_pi: dict[str, int]            # PI name -> item count (ordered by interval)
    closed_dates: list[date]          # individual closed dates (sorted)
    avg_per_week: float
    pi_intervals: list[PIInterval]    # PI definitions used for the bar chart


class FlowVelocityMetric(MetricPlugin):
    """
    Flow Velocity / Throughput metric.

    Counts completed issues (those with a Closed Date) per time period.
    Produces three figures: a daily frequency histogram, a weekly line chart,
    and a per-PI bar chart.

    Set pi_config_path to a JSON file path before calling compute() to use
    custom PI intervals. If empty, quarterly intervals are used by default.
    """

    metric_id = FLOW_VELOCITY
    pi_config_path: str = ""

    def compute(self, data: ReportData, terminology: str) -> MetricResult:
        """
        Aggregate closed issue counts by day, week, and PI (ISO week).

        Issues without a Closed Date are ignored.

        Args:
            data:        Filtered ReportData.
            terminology: Active terminology mode.

        Returns:
            MetricResult with stats (count, date range, avg_per_week)
            and chart_data as _VelocityData.
        """
        closed = sorted(
            [i.closed_date.date() for i in data.issues if i.closed_date is not None]
        )

        warnings: list[str] = []
        if not closed:
            warnings.append("No issues with Closed Date found.")
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        # Daily: how many items closed per day, then frequency distribution
        per_day: Counter[date] = Counter(closed)
        daily_freq: Counter[int] = Counter(per_day.values())

        # Weekly ISO week label
        weekly: Counter[str] = Counter(_iso_week_label(d) for d in closed)

        avg_per_week = statistics.mean(weekly.values()) if weekly else 0.0

        # PI intervals: load from config or fall back to quarterly defaults
        pi_intervals: list[PIInterval] = []
        if self.pi_config_path:
            try:
                pi_intervals = load_pi_config(self.pi_config_path)
            except Exception as exc:
                warnings.append(f"PI config could not be loaded ({exc}); using quarterly defaults.")

        if not pi_intervals:
            pi_intervals = default_quarter_intervals(closed[0], closed[-1])

        # Count issues per PI (preserve interval order; unassigned go to "Other")
        per_pi: dict[str, int] = {iv.name: 0 for iv in pi_intervals}
        unassigned = 0
        for d in closed:
            pi_name = assign_pi(d, pi_intervals)
            if pi_name is not None:
                per_pi[pi_name] += 1
            else:
                unassigned += 1
        if unassigned:
            warnings.append(
                f"{unassigned} issue(s) not covered by any PI interval — excluded from PI chart."
            )

        chart_data = _VelocityData(
            daily_freq=dict(sorted(daily_freq.items())),
            weekly=dict(sorted(weekly.items())),
            per_pi=per_pi,
            closed_dates=closed,
            avg_per_week=round(avg_per_week, 2),
            pi_intervals=pi_intervals,
        )

        from_date = closed[0]
        to_date = closed[-1]
        days_total = (to_date - from_date).days + 1

        stats = dict(
            count=len(closed),
            from_date=str(from_date),
            to_date=str(to_date),
            days_delivered=len(set(closed)),
            avg_per_week=round(avg_per_week, 2),
        )

        return MetricResult(metric_id=self.metric_id, stats=stats,
                            chart_data=chart_data, warnings=warnings)

    def render(self, result: MetricResult, terminology: str) -> list[go.Figure]:
        """
        Render three Flow Velocity figures: daily histogram, weekly line, per-PI bars.

        Args:
            result:      MetricResult from compute().
            terminology: Active terminology mode for labels.

        Returns:
            List of three plotly Figures: [daily_hist, weekly_line, pi_bar].
            Empty list if no chart data is available.
        """
        if not result.chart_data:
            return []

        vd: _VelocityData = result.chart_data
        s = result.stats
        label = term(FLOW_VELOCITY, terminology)

        # --- Daily frequency histogram ---
        x_daily = list(vd.daily_freq.keys())
        y_daily = list(vd.daily_freq.values())
        header_daily = (
            f"{label}:  from:  {s['from_date']}  to:  {s['to_date']}  "
            f"Days delivered:  {s['days_delivered']}"
        )
        fig_daily = go.Figure(go.Bar(
            x=x_daily, y=y_daily,
            marker_color="#4a4a4a",
            text=y_daily, textposition="outside", textfont_color="blue",
        ))
        fig_daily.update_layout(
            title=header_daily, title_font_size=11,
            xaxis_title="Feature per Day", yaxis_title="Freq",
            plot_bgcolor="#e8e8e8", paper_bgcolor="#e8e8e8",
            height=450,
        )

        # --- Weekly line chart ---
        weeks = list(vd.weekly.keys())
        counts_weekly = list(vd.weekly.values())
        fig_weekly = go.Figure(go.Scatter(
            x=weeks, y=counts_weekly, mode="lines+markers",
            line=dict(color="darkcyan", width=2),
            marker=dict(size=5),
            name=label,
        ))
        fig_weekly.update_layout(
            title=f"{label}: Feature per week",
            title_font_size=11,
            xaxis_title="Week", yaxis_title="count",
            plot_bgcolor="#e8e8e8", paper_bgcolor="#e8e8e8",
            height=400,
        )

        # --- Per-PI bar chart ---
        pis = list(vd.per_pi.keys())
        counts_pi = list(vd.per_pi.values())

        # Average per PI (not per week — fixes incorrect avg_per_week usage here)
        avg_per_pi = round(statistics.mean(counts_pi), 2) if counts_pi else 0.0

        # Color bars by PI status relative to today:
        #   index 0 → gray   (first PI may be outside the evaluation window)
        #   current PI        → orange  (today falls within the interval)
        #   completed PIs     → steelblue
        #   future PIs        → lightgray
        today = date.today()
        colors: list[str] = []
        for idx, iv in enumerate(vd.pi_intervals):
            if idx == 0:
                colors.append("gray")
            elif iv.from_date <= today <= iv.to_date:
                colors.append("orange")
            elif iv.to_date < today:
                colors.append("steelblue")
            else:
                colors.append("lightgray")

        # PI axis label: "PI" for custom config, "Quarter" for quarterly defaults
        xaxis_label = "PI" if self.pi_config_path else "Quarter"

        fig_pi = go.Figure(go.Bar(
            x=pis, y=counts_pi,
            marker_color=colors,
            text=counts_pi, textposition="inside",
            textfont=dict(color="white", size=11),
        ))
        fig_pi.add_hline(
            y=avg_per_pi, line_color="red", line_dash="dot",
            annotation_text=f"Avg: {avg_per_pi}",
            annotation_position="right",
        )
        fig_pi.update_layout(
            title=f"{label}: Feature per PI.  Average = {avg_per_pi}",
            title_font_size=11,
            xaxis_title=xaxis_label, yaxis_title="count",
            plot_bgcolor="#e8e8e8", paper_bgcolor="#e8e8e8",
            height=450,
        )

        return [fig_daily, fig_weekly, fig_pi]


register(FlowVelocityMetric())
