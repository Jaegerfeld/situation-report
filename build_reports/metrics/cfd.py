# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
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

import plotly.graph_objects as go

from ..loader import ReportData
from ..terminology import FLOW_DISTRIBUTION, term
from . import register
from .base import MetricPlugin, MetricResult

# Color palette for stages (cycles if more stages than colors)
_STAGE_COLORS = [
    "#e74c3c", "#e67e22", "#f39c12", "#2ecc71", "#1abc9c",
    "#3498db", "#9b59b6", "#34495e", "#95a5a6", "#16a085",
]


@dataclass
class _CfdData:
    """Preprocessed data for the CFD chart."""
    dates: list[str]                    # formatted date labels
    stage_series: dict[str, list[int]]  # stage -> daily counts
    stages: list[str]                   # ordered stage names
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
        dates = [r.day.strftime("%d.%m.%Y") for r in records]

        stage_series: dict[str, list[int]] = {s: [] for s in stages}
        for record in records:
            for s in stages:
                stage_series[s].append(record.stage_counts.get(s, 0))

        # In/Out: first stage as proxy for inflow, last stage for outflow
        in_total = max(stage_series[stages[0]]) if stage_series[stages[0]] else 0
        out_total = max(stage_series[stages[-1]]) if stage_series[stages[-1]] else 0
        ratio = round(in_total / out_total, 2) if out_total else 0.0

        chart_data = _CfdData(
            dates=dates,
            stage_series=stage_series,
            stages=stages,
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

        # Inflow trend line (first stage cumulative max as endpoint)
        if n > 1:
            in_slope = cd.in_total / (n - 1)
            out_slope = cd.out_total / (n - 1)
            trend_x = [cd.dates[0], cd.dates[-1]]

            fig.add_trace(go.Scatter(
                x=trend_x, y=[0, cd.in_total],
                mode="lines", name="Inflow trend",
                line=dict(color="black", width=1.5, dash="solid"),
                showlegend=False,
            ))
            fig.add_trace(go.Scatter(
                x=trend_x, y=[0, cd.out_total],
                mode="lines", name="Outflow trend",
                line=dict(color="black", width=1.5, dash="solid"),
                showlegend=False,
            ))

        fig.update_layout(
            title=f"Ratio In/out  {s['ratio']} : 1",
            title_font_size=12,
            xaxis_title="Date",
            yaxis_title="Count",
            plot_bgcolor="#e8e8e8",
            paper_bgcolor="#e8e8e8",
            legend=dict(orientation="v", x=1.02, y=1),
            height=500,
        )

        return [fig]


register(CfdMetric())
