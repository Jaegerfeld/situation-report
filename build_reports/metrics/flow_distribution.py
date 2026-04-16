# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Implementiert die Flow Distribution Metrik. Zeigt die Verteilung der
#   Issues nach Issuetype als Kreisdiagramm. Optional wird ein zweites
#   Kreisdiagramm für die Statusverteilung gerendert. Alle Issues (offen
#   und geschlossen) fließen in die Berechnung ein, sofern kein Zeitfilter
#   gesetzt ist.
# =============================================================================

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..loader import ReportData
from ..terminology import FLOW_DISTRIBUTION, term
from . import register
from .base import MetricPlugin, MetricResult


@dataclass
class _DistributionData:
    """Frequency distributions for issuetype and status."""
    by_type: dict[str, int]    # issuetype -> count
    by_status: dict[str, int]  # current status -> count
    total: int


class FlowDistributionMetric(MetricPlugin):
    """
    Flow Distribution metric.

    Shows the distribution of issues by issuetype and current status
    as pie charts.
    """

    metric_id = FLOW_DISTRIBUTION

    def compute(self, data: ReportData, terminology: str) -> MetricResult:
        """
        Count issues by issuetype and by current status.

        All issues in the dataset are included regardless of closed state.

        Args:
            data:        Filtered ReportData.
            terminology: Active terminology mode.

        Returns:
            MetricResult with stats (total, type counts) and chart_data
            as _DistributionData.
        """
        warnings: list[str] = []
        if not data.issues:
            warnings.append("No issues found.")
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        by_type = dict(Counter(i.issuetype for i in data.issues).most_common())
        by_status = dict(Counter(i.status for i in data.issues).most_common())

        chart_data = _DistributionData(
            by_type=by_type,
            by_status=by_status,
            total=len(data.issues),
        )
        stats = dict(total=len(data.issues), type_counts=by_type)

        return MetricResult(metric_id=self.metric_id, stats=stats,
                            chart_data=chart_data, warnings=warnings)

    def render(self, result: MetricResult, terminology: str) -> list[go.Figure]:
        """
        Render two pie charts: distribution by issuetype and by current status.

        Args:
            result:      MetricResult from compute().
            terminology: Active terminology mode for labels.

        Returns:
            List with one plotly Figure containing two subplots (side by side),
            or empty list if no data.
        """
        if not result.chart_data:
            return []

        dd: _DistributionData = result.chart_data
        label = term(FLOW_DISTRIBUTION, terminology)

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=["By Issue Type", "By Current Status"],
            specs=[[{"type": "pie"}, {"type": "pie"}]],
        )

        fig.add_trace(go.Pie(
            labels=list(dd.by_type.keys()),
            values=list(dd.by_type.values()),
            hole=0.3,
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        ), row=1, col=1)

        fig.add_trace(go.Pie(
            labels=list(dd.by_status.keys()),
            values=list(dd.by_status.values()),
            hole=0.3,
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        ), row=1, col=2)

        fig.update_layout(
            title=f"{label}  (n={dd.total})",
            title_font_size=12,
            paper_bgcolor="#e8e8e8",
            height=450,
        )

        return [fig]


register(FlowDistributionMetric())
