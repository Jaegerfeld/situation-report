# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       30.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Implementiert die Flow Load / WIP / Aging WIP Metrik. Zeigt für alle
#   Issues in der Statusgruppe "In Progress" (First Date gesetzt, kein Closed
#   Date) die Verweildauer in Tagen je aktueller Stage als gruppierten Boxplot.
#   "To Do"-Issues (kein First Date) gelten nicht als Not Done und werden nicht
#   dargestellt. Stages der Statusgruppe "Done" werden im Boxplot ausgeblendet.
#   Referenzlinien zeigen Median, 85. Perzentil der Cycle Time sowie das
#   konfigurierte Target CT der abgeschlossenen Issues.
#   Die aktuelle Stage eines Issues wird als letzte Stage in Workflow-Reihenfolge
#   mit stage_minutes > 0 bestimmt.
# =============================================================================

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date

import plotly.graph_objects as go

from ..loader import IssueRecord, ReportData
from ..repel import add_repelled_hlines
from ..stage_groups import GROUP_DONE, GROUP_IN_PROGRESS, classify_stages, issue_stage_group
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
    stages_ordered: list[str]          # workflow-ordered stage names (only non-Done stages with items)
    open_count: int                    # number of In Progress issues (not To Do, not Done)
    mean_age: float
    median_age: float
    # Reference lines from closed issues (cycle time)
    ct_median: float | None = None
    ct_pct85: float | None = None
    target_ct_days: int = 90
    done_count: int = 0


class FlowLoadMetric(MetricPlugin):
    """
    Flow Load / WIP / Aging WIP metric.

    Shows the age distribution of open (not-done) issues per workflow stage
    as a grouped boxplot with cycle time reference lines.
    """

    metric_id = FLOW_LOAD
    target_ct: int = 90

    def compute(self, data: ReportData, terminology: str) -> MetricResult:
        """
        Compute age of all In Progress issues grouped by current stage.

        Only issues in the In Progress status group (First Date set, no Closed
        Date) count as "Not Done" and are included in the chart. To Do issues
        (no First Date) have not yet entered the active workflow and are excluded.

        Stages classified as Done are not shown as boxplot columns — they are
        irrelevant for an Aging WIP view.

        Cycle time stats (median, 85th percentile) are computed from closed
        issues and used as reference lines in the chart alongside target_ct.

        Args:
            data:        Filtered ReportData.
            terminology: Active terminology mode.

        Returns:
            MetricResult with stats and chart_data as _LoadData.
        """
        today = date.today()
        warnings: list[str] = []

        open_issues = [i for i in data.issues if issue_stage_group(i) == GROUP_IN_PROGRESS]
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

        # Keep only stages that have issues AND are not classified as Done
        stage_groups = classify_stages(data.stages, data.first_stage, data.closed_stage)
        active_stages = [
            s for s in data.stages
            if by_stage.get(s) and stage_groups.get(s) != GROUP_DONE
        ]
        all_ages = [a for ages in by_stage.values() for a in ages]

        mean_age = statistics.mean(all_ages) if all_ages else 0.0
        median_age = statistics.median(all_ages) if all_ages else 0.0

        # Cycle time reference from closed issues
        ct_median = ct_p85 = None
        done_count = 0
        if closed_issues:
            ct_days = sorted([
                (i.closed_date - i.first_date).total_seconds() / 86400
                for i in closed_issues
                if (i.closed_date - i.first_date).total_seconds() > 0
            ])
            if ct_days:
                n = len(ct_days)
                ct_median = round(statistics.median(ct_days), 1)
                ct_p85 = round(ct_days[int(n * 0.85)], 1)
                done_count = n

        chart_data = _LoadData(
            by_stage={s: by_stage[s] for s in active_stages},
            stages_ordered=active_stages,
            open_count=len(open_issues),
            mean_age=round(mean_age, 1),
            median_age=round(median_age, 1),
            ct_median=ct_median,
            ct_pct85=ct_p85,
            target_ct_days=self.target_ct,
            done_count=done_count,
        )

        stats = dict(
            open_count=len(open_issues),
            mean_age=round(mean_age, 1),
            median_age=round(median_age, 1),
            done_count=done_count,
            ct_median=ct_median,
            ct_pct85=ct_p85,
            target_ct_days=self.target_ct,
        )

        return MetricResult(metric_id=self.metric_id, stats=stats,
                            chart_data=chart_data, warnings=warnings)

    def render(self, result: MetricResult, terminology: str) -> list[go.Figure]:
        """
        Render a grouped boxplot of open issue ages per workflow stage.

        Reference lines show CT Median (blue), CT P85 (red), and Target CT
        (green) from closed issues. Individual issue ages are shown as dots.

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

        # Legend entries for reference lines (dummy traces)
        # Target CT is always shown; CT Median and P85 only when closed issues exist
        if ld.ct_median is not None:
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode="lines",
                name=f"CT Median: {ld.ct_median}d",
                line=dict(color="blue", dash="dot", width=1.5),
                showlegend=True,
            ))
        if ld.ct_pct85 is not None:
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode="lines",
                name=f"CT P85: {ld.ct_pct85}d",
                line=dict(color="red", dash="dot", width=1.5),
                showlegend=True,
            ))
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="lines",
            name=f"Target CT: {ld.target_ct_days}d",
            line=dict(color="green", dash="dot", width=1.5),
            showlegend=True,
        ))

        # Reference lines — repelled so annotations don't overlap when values are close
        all_ages = [a for ages in ld.by_stage.values() for a in ages]
        y_max = max(all_ages) if all_ages else 1.0
        hlines = []
        if ld.ct_median is not None:
            hlines.append((ld.ct_median, "blue", "dot", f"{ld.ct_median}d"))
        if ld.ct_pct85 is not None:
            hlines.append((ld.ct_pct85, "red", "dot", f"{ld.ct_pct85}d"))
        hlines.append((ld.target_ct_days, "green", "dot", f"{ld.target_ct_days}d"))
        add_repelled_hlines(fig, lines=hlines, y_max=y_max, fig_height=550)

        ct_footer = ""
        if ld.ct_median is not None:
            ct_footer = (
                f"Cycle Time Reference | Median: {ld.ct_median}d | "
                f"P85: {ld.ct_pct85}d | Target CT: {ld.target_ct_days}d | "
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
