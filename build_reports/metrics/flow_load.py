# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       25.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Implementiert die Flow Load / WIP / Aging WIP Metrik. Zeigt für alle
#   offenen Issues (kein Closed Date) die Verweildauer in Tagen je aktueller
#   Stage als gruppierten Boxplot. Referenzlinien zeigen Mean und Median der
#   abgeschlossenen Issues (aus der Flow Time Metrik). Die aktuelle Stage eines
#   Issues wird als letzte Stage in Workflow-Reihenfolge mit stage_minutes > 0
#   bestimmt.
# =============================================================================

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date

import plotly.graph_objects as go

from ..loader import IssueRecord, ReportData
from ..terminology import FLOW_LOAD, term
from . import register
from .base import MetricPlugin, MetricResult


def _current_stage(issue: IssueRecord, stages: list[str]) -> str:
    """
    Determine the current stage of an issue from its stage_minutes.

    Returns the last stage in workflow order that has minutes > 0.
    Falls back to the first stage if no stage has any time recorded.

    Args:
        issue:  IssueRecord with stage_minutes populated.
        stages: Ordered list of workflow stage names.

    Returns:
        Name of the current stage.
    """
    for stage in reversed(stages):
        if issue.stage_minutes.get(stage, 0) > 0:
            return stage
    return stages[0] if stages else "Unknown"


def _age_days(issue: IssueRecord, reference: date) -> float:
    """
    Compute the age of an open issue in days from first_date (or created) to reference.

    Args:
        issue:     The open issue.
        reference: Reference date (typically today).

    Returns:
        Age in days as a float.
    """
    start = issue.first_date or issue.created
    if start is None:
        return 0.0
    return max(0.0, (reference - start.date()).days)


@dataclass
class _LoadData:
    """Aggregated data for the Aging WIP chart."""
    by_stage: dict[str, list[float]]   # stage -> list of ages in days
    stages_ordered: list[str]          # workflow-ordered stage names (only stages with items)
    open_count: int
    mean_age: float
    median_age: float
    # Reference lines from closed issues (cycle time)
    ct_mean: float | None = None
    ct_median: float | None = None
    ct_pct85: float | None = None
    ct_pct95: float | None = None
    done_count: int = 0


class FlowLoadMetric(MetricPlugin):
    """
    Flow Load / WIP / Aging WIP metric.

    Shows the age distribution of open (not-done) issues per workflow stage
    as a grouped boxplot with cycle time reference lines.
    """

    metric_id = FLOW_LOAD

    def compute(self, data: ReportData, terminology: str) -> MetricResult:
        """
        Compute age of all open issues grouped by current stage.

        Open issues are those without a Closed Date. Age is measured from
        First Date (or Created if First Date is absent) to today.

        Cycle time stats (mean, median, 85th/95th percentile) are computed
        from closed issues and used as reference lines in the chart.

        Args:
            data:        Filtered ReportData.
            terminology: Active terminology mode.

        Returns:
            MetricResult with stats and chart_data as _LoadData.
        """
        today = date.today()
        warnings: list[str] = []

        open_issues = [i for i in data.issues if i.closed_date is None]
        closed_issues = [i for i in data.issues if i.closed_date is not None
                         and i.first_date is not None]

        if not open_issues:
            warnings.append("No open issues found.")
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        # Group open issues by current stage
        by_stage: dict[str, list[float]] = {s: [] for s in data.stages}
        for issue in open_issues:
            stage = _current_stage(issue, data.stages)
            age = _age_days(issue, today)
            by_stage.setdefault(stage, []).append(age)

        # Remove stages with no open issues
        active_stages = [s for s in data.stages if by_stage.get(s)]
        all_ages = [a for ages in by_stage.values() for a in ages]

        mean_age = statistics.mean(all_ages) if all_ages else 0.0
        median_age = statistics.median(all_ages) if all_ages else 0.0

        # Cycle time reference from closed issues
        ct_mean = ct_median = ct_p85 = ct_p95 = None
        done_count = 0
        if closed_issues:
            ct_days = sorted([
                (i.closed_date - i.first_date).total_seconds() / 86400
                for i in closed_issues
                if (i.closed_date - i.first_date).total_seconds() > 0
            ])
            if ct_days:
                n = len(ct_days)
                ct_mean = round(statistics.mean(ct_days), 1)
                ct_median = round(statistics.median(ct_days), 1)
                ct_p85 = round(ct_days[int(n * 0.85)], 1)
                ct_p95 = round(ct_days[int(n * 0.95)], 1)
                done_count = n

        chart_data = _LoadData(
            by_stage={s: by_stage[s] for s in active_stages},
            stages_ordered=active_stages,
            open_count=len(open_issues),
            mean_age=round(mean_age, 1),
            median_age=round(median_age, 1),
            ct_mean=ct_mean,
            ct_median=ct_median,
            ct_pct85=ct_p85,
            ct_pct95=ct_p95,
            done_count=done_count,
        )

        stats = dict(
            open_count=len(open_issues),
            mean_age=round(mean_age, 1),
            median_age=round(median_age, 1),
            done_count=done_count,
            ct_mean=ct_mean,
            ct_median=ct_median,
        )

        return MetricResult(metric_id=self.metric_id, stats=stats,
                            chart_data=chart_data, warnings=warnings)

    def render(self, result: MetricResult, terminology: str) -> list[go.Figure]:
        """
        Render a grouped boxplot of open issue ages per workflow stage.

        Reference lines show cycle time mean, median, 85th and 95th percentile
        from closed issues. Individual issue ages are shown as overlay dots.

        Args:
            result:      MetricResult from compute().
            terminology: Active terminology mode for labels.

        Returns:
            List with one plotly Figure, or empty list if no data.
        """
        if not result.chart_data:
            return []

        ld: _LoadData = result.chart_data
        s = result.stats
        label = term(FLOW_LOAD, terminology)

        header = (
            f"Flow Load: Aging Work in Progress  |  "
            f"Mean {ld.mean_age} | Median: {ld.median_age} | "
            f"# Not done items: {ld.open_count}"
        )

        fig = go.Figure()

        for stage in ld.stages_ordered:
            ages = ld.by_stage[stage]
            fig.add_trace(go.Box(
                y=ages, name=stage,
                boxpoints="all", jitter=0.3, pointpos=0,
                marker=dict(color="red", size=4, opacity=0.6),
                line=dict(color="black"),
                fillcolor="white",
                showlegend=False,
            ))

        # Reference lines (cycle time from done items)
        ref_lines = [
            (ld.ct_mean,   "blue",   "dash",     "CT Mean"),
            (ld.ct_median, "red",    "dot",      "CT Median"),
            (ld.ct_pct85,  "green",  "dashdot",  "CT P85"),
            (ld.ct_pct95,  "purple", "longdash", "CT P95"),
        ]
        for val, color, dash, lbl in ref_lines:
            if val is not None:
                # Dummy trace for legend entry
                fig.add_trace(go.Scatter(
                    x=[None], y=[None],
                    mode="lines",
                    name=f"{lbl}: {val}d",
                    line=dict(color=color, dash=dash, width=1.5),
                    showlegend=True,
                ))
                fig.add_hline(
                    y=val, line_color=color, line_dash=dash, line_width=1.5,
                    annotation_text=f"{val}d",
                    annotation_position="right",
                    annotation_font_size=9,
                )

        ct_footer = ""
        if ld.ct_mean is not None:
            ct_footer = (
                f"Current CycleTime | Mean: {ld.ct_mean} | Median: {ld.ct_median} | "
                f"# Done items: {ld.done_count}"
            )

        fig.update_layout(
            title=header,
            title_font_size=11,
            xaxis_title="Stage",
            yaxis_title="Total Age (days)",
            plot_bgcolor="#e8e8e8",
            paper_bgcolor="#e8e8e8",
            showlegend=True,
            legend=dict(
                title="Cycle Time Reference<br>(from closed issues)",
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#bdc3c7",
                borderwidth=1,
                font=dict(size=10),
            ),
            height=550,
        )

        # Add annotations after update_layout so they don't get merged with hline annotations
        if ct_footer:
            fig.add_annotation(
                text=ct_footer, xref="paper", yref="paper",
                x=1.0, y=-0.12, showarrow=False,
                font=dict(size=10), xanchor="right",
            )
        for stage in ld.stages_ordered:
            fig.add_annotation(
                x=stage, y=1.0,
                xref="x", yref="paper",
                text=f"n={len(ld.by_stage[stage])}",
                showarrow=False,
                font=dict(size=9),
                bgcolor="white",
                bordercolor="#bdc3c7",
                borderwidth=1,
                xanchor="center",
                yanchor="top",
            )

        return [fig]


register(FlowLoadMetric())
