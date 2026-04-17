# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       17.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Implementiert das Cumulative Flow Diagram (CFD). Liest die täglichen
#   Stage-Zählungen aus CFD.xlsx und erzeugt ein gestapeltes Flächendiagramm.
#   Zwei lineare Trendlinien zeigen den Inflow (erste Stage, kumulativ) und
#   den Outflow (letzte Stage, kumulativ). Das In/Out-Verhältnis wird im Titel
#   ausgewiesen. Issues, die auf 0 fallen, werden aus dem Verhältnis heraus-
#   gehalten.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import plotly.graph_objects as go

from ..loader import ReportData
from ..terminology import FLOW_DISTRIBUTION, term
from . import register
from .base import MetricPlugin, MetricResult

_MONTH_ABBR_CFD = [
    "", "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
]


_WEEK_LABEL_HTML = '<span style="font-size:8px; color:#aaa">{week}</span>'


def _cfd_tick_labels(
    dates: list[str],
) -> tuple[list[str], list[str]]:
    """
    Generate x-axis tick positions and labels for the CFD chart.

    Month boundaries receive a prominent label (e.g. "Jan 2025");
    ISO week Mondays that are not a month start receive a small HTML-
    formatted label ("<span ...>W03</span>") so weeks render visually
    smaller than month markers and do not overlap.

    Args:
        dates: Ordered list of ISO date strings present in the CFD data.

    Returns:
        Tuple of (tickvals, ticktext) for plotly xaxis configuration.
    """
    if not dates:
        return [], []

    d_start = date.fromisoformat(dates[0])
    d_end = date.fromisoformat(dates[-1])

    tickvals: list[str] = []
    ticktext: list[str] = []
    seen: set[str] = set()

    # Walk day by day through the range
    d = d_start
    while d <= d_end:
        iso = d.isoformat()
        is_month_start = d.day == 1
        is_monday = d.weekday() == 0  # 0 = Monday

        if is_month_start:
            label = f"{_MONTH_ABBR_CFD[d.month]} {d.year}"
            tickvals.append(iso)
            ticktext.append(label)
            seen.add(iso)
        elif is_monday and iso not in seen:
            week = d.isocalendar().week
            tickvals.append(iso)
            ticktext.append(_WEEK_LABEL_HTML.format(week=f"W{week:02d}"))
            seen.add(iso)

        d += timedelta(days=1)

    return tickvals, ticktext


# Color palette for stages (cycles if more stages than colors)
_STAGE_COLORS = [
    "#e74c3c", "#e67e22", "#f39c12", "#2ecc71", "#1abc9c",
    "#3498db", "#9b59b6", "#34495e", "#95a5a6", "#16a085",
]


@dataclass
class _CfdData:
    """Preprocessed data for the CFD chart."""
    dates: list[str]                    # ISO date strings "YYYY-MM-DD" (for plotly date axis)
    stage_series: dict[str, list[int]]  # stage -> daily counts
    stages: list[str]                   # ordered stage names
    totals: list[int]                   # sum of all stages per day (top of stacked area)
    in_total: int                       # cumulative total first-stage at end
    out_total: int                      # cumulative total last-stage at end
    ratio: float                        # in/out ratio


class CfdMetric(MetricPlugin):
    """
    Cumulative Flow Diagram metric.

    Reads daily stage count data from CFD.xlsx and renders a stacked area chart
    with inflow/outflow trend lines and an In/Out ratio in the title.
    """

    metric_id = "cfd"

    def compute(self, data: ReportData, terminology: str) -> MetricResult:
        """
        Prepare CFD data for rendering.

        Computes the In/Out ratio as the ratio of the cumulative count
        in the first stage versus the last stage at the end of the period.

        Args:
            data:        Filtered ReportData (cfd records must be populated).
            terminology: Active terminology mode (not used for CFD labels).

        Returns:
            MetricResult with stats (in_total, out_total, ratio) and
            chart_data as _CfdData.
        """
        warnings: list[str] = []
        if not data.cfd:
            warnings.append("No CFD data available.")
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        stages = data.stages
        if not stages:
            warnings.append("No stages defined in data.")
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        records = sorted(data.cfd, key=lambda r: r.day)
        dates = [r.day.isoformat() for r in records]  # ISO "YYYY-MM-DD" for plotly date axis

        stage_series: dict[str, list[int]] = {s: [] for s in stages}
        for record in records:
            for s in stages:
                stage_series[s].append(record.stage_counts.get(s, 0))

        # Total stacked height per day (= top of first-stage area)
        totals = [
            sum(stage_series[s][i] for s in stages)
            for i in range(len(records))
        ]

        # In/Out ratio: total inflow (top of stack at end) vs outflow (last stage at end)
        in_total = totals[-1] if totals else 0
        out_total = stage_series[stages[-1]][-1] if stage_series[stages[-1]] else 0
        ratio = round(in_total / out_total, 2) if out_total else 0.0

        chart_data = _CfdData(
            dates=dates,
            stage_series=stage_series,
            stages=stages,
            totals=totals,
            in_total=in_total,
            out_total=out_total,
            ratio=ratio,
        )
        stats = dict(in_total=in_total, out_total=out_total, ratio=ratio,
                     days=len(records))

        return MetricResult(metric_id=self.metric_id, stats=stats,
                            chart_data=chart_data, warnings=warnings)

    def render(self, result: MetricResult, terminology: str) -> list[go.Figure]:
        """
        Render the Cumulative Flow Diagram as a stacked area chart.

        Stages are stacked with the first stage at the top (highest cumulative).
        Two diagonal trend lines show the overall inflow and outflow slopes.

        Args:
            result:      MetricResult from compute().
            terminology: Active terminology mode.

        Returns:
            List with one plotly Figure, or empty list if no data.
        """
        if not result.chart_data:
            return []

        cd: _CfdData = result.chart_data
        s = result.stats
        n = len(cd.dates)

        fig = go.Figure()

        # Stacked area traces — reverse order so first stage is on top
        for i, stage in enumerate(reversed(cd.stages)):
            color = _STAGE_COLORS[i % len(_STAGE_COLORS)]
            fig.add_trace(go.Scatter(
                x=cd.dates,
                y=cd.stage_series[stage],
                mode="lines",
                name=stage,
                stackgroup="cfd",
                line=dict(width=0.5, color=color),
                fillcolor=color,
                hovertemplate=f"<b>{stage}</b><br>%{{x}}<br>Count: %{{y}}<extra></extra>",
            ))

        # Trend lines: anchored to actual start/end values
        # Upper trend: top of stacked area (total of all stages = "First" stage top edge)
        # Lower trend: last stage (Closed/Done) values
        if n > 1:
            trend_x = [cd.dates[0], cd.dates[-1]]
            last_stage = cd.stages[-1]

            fig.add_trace(go.Scatter(
                x=trend_x,
                y=[cd.totals[0], cd.totals[-1]],
                mode="lines", name="Inflow trend",
                line=dict(color="black", width=1.5, dash="solid"),
                showlegend=False,
            ))
            fig.add_trace(go.Scatter(
                x=trend_x,
                y=[cd.stage_series[last_stage][0], cd.stage_series[last_stage][-1]],
                mode="lines", name="Outflow trend",
                line=dict(color="black", width=1.5, dash="solid"),
                showlegend=False,
            ))

        # X-axis ticks: months large, calendar weeks small
        tickvals, ticktext = _cfd_tick_labels(cd.dates)

        fig.update_layout(
            title=f"Ratio In/out  {s['ratio']} : 1",
            title_font_size=12,
            xaxis_title="Date",
            yaxis_title="Count",
            plot_bgcolor="#e8e8e8",
            paper_bgcolor="#e8e8e8",
            legend=dict(orientation="v", x=1.02, y=1),
            height=500,
            xaxis=dict(
                type="date",
                tickmode="array",
                tickvals=tickvals,
                ticktext=ticktext,
            ),
        )

        return [fig]


register(CfdMetric())
