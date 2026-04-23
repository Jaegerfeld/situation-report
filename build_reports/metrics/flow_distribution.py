# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       24.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Implementiert die Flow Distribution Metrik. Zeigt drei Kreisdiagramme:
#   (1) Verteilung nach Issuetype (Anzahl), (2) Stage-Prominenz – welcher
#   Stage pro Issue die meiste aktive Zeit verbracht wurde, aggregiert über
#   alle Issues; für geschlossene Issues wird die terminale Done-Stage
#   (= issue.status) ausgeschlossen, damit akkumulierte Wartezeit nach dem
#   Schließen nicht dominiert – und (3) durchschnittliche Cycle Time in
#   Tagen pro Issuetype. Chart 3 berücksichtigt nur Issues mit First Date
#   und Closed Date (CT > 0).
# =============================================================================

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..loader import ReportData
from ..terminology import FLOW_DISTRIBUTION, term
from . import register
from .base import MetricPlugin, MetricResult


@dataclass
class _DistributionData:
    """Frequency distributions and cycle time averages for flow distribution charts."""

    by_type: dict[str, int]        # issuetype -> count
    by_prominence: dict[str, int]  # stage -> count of issues where it was the longest active stage
    ct_by_type: dict[str, float]   # issuetype -> average cycle time in days (CT > 0 only)
    total: int
    prominence_n: int              # number of issues contributing to prominence (stage_minutes > 0)


class FlowDistributionMetric(MetricPlugin):
    """
    Flow Distribution metric.

    Shows three pie charts: issue distribution by type, status prominence
    (which stage each issue spent the most time in), and average cycle time
    by issue type.
    """

    metric_id = FLOW_DISTRIBUTION

    def compute(self, data: ReportData, terminology: str) -> MetricResult:
        """
        Compute issue distribution, stage prominence, and avg cycle time per type.

        All issues are counted for charts 1 and 2. Chart 3 uses only issues
        with both first_date and closed_date and a positive cycle time.

        Args:
            data:        Filtered ReportData.
            terminology: Active terminology mode.

        Returns:
            MetricResult with stats and chart_data as _DistributionData.
        """
        warnings: list[str] = []
        if not data.issues:
            warnings.append("No issues found.")
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        by_type = dict(Counter(i.issuetype for i in data.issues).most_common())

        by_prominence: dict[str, int] = {}
        prominence_n = 0
        for issue in data.issues:
            if not (issue.stage_minutes and any(v > 0 for v in issue.stage_minutes.values())):
                continue
            # For closed issues exclude the terminal Done stage (current status) so that
            # time accumulated after closing does not dominate the result.
            candidates = {
                s: m for s, m in issue.stage_minutes.items()
                if issue.closed_date is None or s != issue.status
            }
            if not candidates or not any(v > 0 for v in candidates.values()):
                continue
            prominence_n += 1
            stage = max(candidates, key=candidates.__getitem__)
            by_prominence[stage] = by_prominence.get(stage, 0) + 1

        ct_buckets: dict[str, list[float]] = defaultdict(list)
        for issue in data.issues:
            if issue.first_date and issue.closed_date:
                ct = (issue.closed_date - issue.first_date).total_seconds() / 86400
                if ct > 0:
                    ct_buckets[issue.issuetype].append(ct)
        ct_by_type = {k: sum(v) / len(v) for k, v in ct_buckets.items()}

        chart_data = _DistributionData(
            by_type=by_type,
            by_prominence=by_prominence,
            ct_by_type=ct_by_type,
            total=len(data.issues),
            prominence_n=prominence_n,
        )
        stats = dict(
            total=len(data.issues),
            type_counts=by_type,
            prominence_counts=by_prominence,
            prominence_n=prominence_n,
            ct_by_type=ct_by_type,
        )

        return MetricResult(metric_id=self.metric_id, stats=stats,
                            chart_data=chart_data, warnings=warnings)

    def render(self, result: MetricResult, terminology: str) -> list[go.Figure]:
        """
        Render two pie charts (by issue type, stage prominence) and one bar chart
        (avg cycle time by issue type).

        Args:
            result:      MetricResult from compute().
            terminology: Active terminology mode for labels.

        Returns:
            List with one plotly Figure containing three subplots, or empty list
            if no data.
        """
        if not result.chart_data:
            return []

        dd: _DistributionData = result.chart_data
        label = term(FLOW_DISTRIBUTION, terminology)

        fig = make_subplots(
            rows=1, cols=3,
            subplot_titles=[
                "By Issue Type",
                f"Stage Prominence (n={dd.prominence_n})",
                "Avg Cycle Time by Type (days)",
            ],
            specs=[[{"type": "pie"}, {"type": "pie"}, {"type": "xy"}]],
        )

        fig.add_trace(go.Pie(
            labels=list(dd.by_type.keys()),
            values=list(dd.by_type.values()),
            hole=0.3,
            textinfo="label+percent+value",
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        ), row=1, col=1)

        fig.add_trace(go.Pie(
            labels=list(dd.by_prominence.keys()),
            values=list(dd.by_prominence.values()),
            hole=0.3,
            textinfo="label+percent+value",
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        ), row=1, col=2)

        ct_labels = list(dd.ct_by_type.keys())
        ct_values = [round(v, 1) for v in dd.ct_by_type.values()]
        fig.add_trace(go.Bar(
            x=ct_labels,
            y=ct_values,
            text=[f"{v:.1f}d" for v in ct_values],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Avg CT: %{y:.1f}d<extra></extra>",
        ), row=1, col=3)

        fig.update_layout(
            title=f"{label}  (n={dd.total})",
            title_font_size=12,
            paper_bgcolor="#e8e8e8",
            height=450,
            showlegend=False,
        )
        fig.update_yaxes(title_text="days", row=1, col=3)

        return [fig]


register(FlowDistributionMetric())
